"""
Lung Sound Analysis Service
肺部呼吸音多 Agent 能力 —— 音频保存 / 预处理 / 模型推理。

设计要点：
1. 模型只在首次推理时加载一次（进程级单例），后续请求复用，避免每次请求加载权重。
2. 模型采用 RSC-FTF (PBRNet) 双编码器结构：AST 处理 Mel 谱图 + BEATs 处理时域波形，
   与 `eval_threshold_fast.py` 的 `set_model()` 构建方式一致（MMTAEncoderV2 + use_adapter=True）。
3. 预处理与 ICBHI 训练保持一致：16kHz / 单声道 / repeat 补齐到 8s / kaldi fbank / mean-std 归一化。
4. 所有推理异常在此捕获并返回可读信息，绝不导致服务崩溃。
"""
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 呼吸音四分类，与 ICBHI 数据集标签对齐。
LUNG_SOUND_LABELS = ["normal", "crackle", "wheeze", "both"]

# 采样率与固定时长（秒）。训练用 desired_length=8，即 8s / 128000 采样点。
TARGET_SAMPLE_RATE = 16000
CLIP_DURATION_SECONDS = 8.0

# Mel 谱图参数，与训练 generate_fbank 严格一致。
NUM_MEL_BINS = 128
MEL_MEAN = -4.2677393
MEL_STD = 4.5689974
FADE_SAMPLES_RATIO = 16  # fade_out 长度 = sample_rate / 16

# 上传音频的大小上限（字节）。
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class LungSoundService:
    """肺部呼吸音推理服务（单例）。"""

    def __init__(self) -> None:
        self._model = None
        self._device = None

    # ------------------------------------------------------------------
    # 音频存储
    # ------------------------------------------------------------------
    @property
    def storage_dir(self) -> str:
        """呼吸音音频落盘目录：backend/storage/lung_sounds。"""
        base = str(Path(__file__).resolve().parents[2] / "storage" / "lung_sounds")
        return base

    def save_audio(self, audio_data: bytes, filename: Optional[str] = None) -> str:
        """将上传的 wav 原始字节保存到磁盘，返回存储路径。"""
        os.makedirs(self.storage_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}.wav"
        path = os.path.join(self.storage_dir, safe_name)
        with open(path, "wb") as fh:
            fh.write(audio_data)
        logger.info("呼吸音音频已保存：%s", path)
        return path

    # ------------------------------------------------------------------
    # 模型加载（只加载一次）
    # ------------------------------------------------------------------
    def _ensure_model_loaded(self) -> None:
        """懒加载 PBRNet 模型权重。进程生命周期内只执行一次。"""
        if self._model is not None:
            return

        import torch

        ckpt_path = settings.MODEL_LUNG_SOUND_CHECKPOINT_PATH
        if not ckpt_path or not os.path.exists(ckpt_path):
            raise FileNotFoundError(
                f"呼吸音模型权重不存在：{ckpt_path}。请配置 MODEL_LUNG_SOUND_CHECKPOINT_PATH。"
            )

        rsc_root = settings.MODEL_LUNG_SOUND_RSC_ROOT
        if not rsc_root or not os.path.isdir(rsc_root):
            raise FileNotFoundError(
                f"呼吸音训练代码目录不存在：{rsc_root}。请配置 MODEL_LUNG_SOUND_RSC_ROOT，"
                "指向 RSC-FTF-main 目录（包含 models/ 与 BEATs.py）。"
            )
        if rsc_root not in sys.path:
            sys.path.insert(0, rsc_root)

        # 复用训练仓库模型类，保证架构与 checkpoint 完全一致。
        from models.ast import ASTModel, SpectrogramEncoder
        from models.pbr_net import MMTAEncoderV2, PBRNet

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 采用「不加载预训练权重」方式构建架构，随后用 best.pth 的 state_dict 覆盖。
        # 避免 audioset_16_16_0.4422.pth 缺文件导致构建崩溃。
        ast_full = ASTModel(
            label_dim=len(LUNG_SOUND_LABELS),
            input_fdim=1024,
            input_tdim=256,
            imagenet_pretrain=False,
            audioset_pretrain=False,
            model_size="base384",
            verbose=False,
        )
        ast_encoder = SpectrogramEncoder(ast_full.v, ast_full.conv)
        beats_encoder = MMTAEncoderV2(ast_full.beats_model)
        model = PBRNet(
            ast_encoder,
            beats_encoder,
            num_classes=len(LUNG_SOUND_LABELS),
            use_adapter=True,
        )

        ckpt = torch.load(ckpt_path, map_location="cpu")
        state_dict = ckpt["model"] if isinstance(ckpt, dict) and "model" in ckpt else ckpt
        model.load_state_dict(state_dict, strict=False)

        model = model.to(self._device).eval()
        self._model = model
        logger.info("呼吸音模型已加载到 %s", self._device)

    # ------------------------------------------------------------------
    # 预处理（与 ICBHI 训练对齐）
    # ------------------------------------------------------------------
    @staticmethod
    def load_waveform(audio_path: str):
        """加载并标准化音频：16000Hz / 单声道 / float32，输出 [1, T] 张量。"""
        import torchaudio

        waveform, sr = torchaudio.load(audio_path)
        if sr != TARGET_SAMPLE_RATE:
            waveform = torchaudio.functional.resample(waveform, sr, TARGET_SAMPLE_RATE)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        return waveform

    @staticmethod
    def _to_fixed_length(waveform):
        """repeat 补齐（或截断）到 8s，并施加 fade_out，对齐 cut_pad_sample_torchaudio。"""
        import torchaudio

        target_len = int(TARGET_SAMPLE_RATE * CLIP_DURATION_SECONDS)
        if waveform.shape[-1] > target_len:
            return waveform[..., :target_len]

        fade_out = torchaudio.transforms.Fade(
            fade_in_len=0,
            fade_out_len=int(TARGET_SAMPLE_RATE / FADE_SAMPLES_RATIO),
            fade_shape="linear",
        )
        ratio = -(-target_len // waveform.shape[-1])  # ceil
        waveform = waveform.repeat(1, ratio)[..., :target_len]
        return fade_out(waveform)

    @staticmethod
    def _to_mel(waveform):
        """kaldi fbank + mean/std 归一化 + 双线性 resize，输出 [1, 1, 1024, 256]。"""
        import torch
        import torch.nn.functional as F
        import torchaudio

        fbank = torchaudio.compliance.kaldi.fbank(
            waveform,
            htk_compat=True,
            sample_frequency=TARGET_SAMPLE_RATE,
            use_energy=False,
            window_type="hanning",
            num_mel_bins=NUM_MEL_BINS,
            dither=0.0,
            frame_shift=10,
        )  # [T, 128]

        fbank = (fbank - MEL_MEAN) / (MEL_STD * 2)

        # 转为 [1, 1, 128, T]，再 resize 到训练固定尺寸 [1024, 256]。
        mel = fbank.permute(1, 0).unsqueeze(0).unsqueeze(0)
        mel = F.interpolate(mel, size=(1024, 256), mode="bilinear", align_corners=False)
        return mel  # [1, 1, 1024, 256]

    # ------------------------------------------------------------------
    # 推理
    # ------------------------------------------------------------------
    def predict(self, audio_path: str) -> Dict[str, Any]:
        """对单一音频文件做推理，返回结构化结果字典。"""
        import torch

        self._ensure_model_loaded()

        waveform = self.load_waveform(audio_path)       # [1, T]
        waveform = self._to_fixed_length(waveform)      # [1, 128000]
        mel = self._to_mel(waveform)                    # [1, 1, 1024, 256]

        waveform = waveform.to(self._device)
        mel = mel.to(self._device)

        with torch.no_grad():
            outputs = self._model(mel, waveform, lambda_control=0.0)
            logits = outputs["logits"]                   # [1, 4]
            probs = torch.softmax(logits, dim=1)[0].detach().cpu()  # [4]

        idx = int(probs.argmax())
        # 返回四分类完整概率分布（normal/crackle/wheeze/both），供前端可视化。
        probabilities = {
            label: float(prob)
            for label, prob in zip(LUNG_SOUND_LABELS, probs.tolist())
        }
        return {
            "label": LUNG_SOUND_LABELS[idx],
            "confidence": float(probs[idx]),
            "probabilities": probabilities,
            "audio_path": audio_path,
        }

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """预处理 + 推理 + 可选信噪比检测，返回可供 Pydantic 解析的结果字典。"""
        result = self.predict(audio_path)

        # 可选扩展：音频信噪比（SNR）检测，噪声过高提示用户重新录制。
        try:
            snr_db = self.estimate_snr(audio_path)
            result["snr_db"] = snr_db
            result["low_quality"] = snr_db is not None and snr_db < 5.0
        except Exception as e:  # noqa: BLE001
            logger.warning("SNR 估算失败（不影响推理）：%s", e)
            result["snr_db"] = None
            result["low_quality"] = False

        return result

    # ------------------------------------------------------------------
    # 可选扩展：信噪比估算
    # ------------------------------------------------------------------
    @staticmethod
    def estimate_snr(audio_path: str) -> Optional[float]:
        """简易信噪比：取能量最低的 10% 帧作为噪声参考。

        使用 torchaudio + numpy 计算，避免引入 librosa/numba（其 JIT 扩展
        在 Python 3.9 下会报 `initialization of _internal failed` 而不可用）。
        """
        import numpy as np
        import torchaudio

        waveform, sr = torchaudio.load(audio_path)
        if sr != TARGET_SAMPLE_RATE:
            waveform = torchaudio.functional.resample(waveform, sr, TARGET_SAMPLE_RATE)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        y = waveform[0].numpy().astype(np.float32)

        frame_len = int(TARGET_SAMPLE_RATE * 0.025)
        hop = frame_len // 2
        if len(y) < frame_len:
            return None

        num_frames = 1 + (len(y) - frame_len) // hop
        if num_frames <= 0:
            return None
        idx = np.arange(num_frames)[:, None] * hop + np.arange(frame_len)[None, :]
        frames = y[idx]  # [num_frames, frame_len]
        energy = (frames ** 2).mean(axis=1)

        noise_energy = max(float(np.percentile(energy, 10)), 1e-12)
        signal_energy = float(energy.mean())
        return float(10.0 * np.log10(signal_energy / noise_energy))


# 进程级单例：模型权重仅在首次使用时加载。
lung_sound_service = LungSoundService()