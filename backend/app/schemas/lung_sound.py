from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, Dict


class LungSoundResult(BaseModel):
    """
    肺部呼吸音推理结果。
    标签与 ICBHI 数据集四分类保持一致：normal / crackle / wheeze / both。
    """
    label: Literal["normal", "crackle", "wheeze", "both"] = Field(
        ..., description="呼吸音分类标签（ICBHI 四分类）"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="模型置信度，0~1")
    probabilities: Optional[Dict[str, float]] = Field(
        None, description="四分类完整概率分布 {normal, crackle, wheeze, both}，各值 0~1 且和≈1"
    )
    audio_path: str = Field(..., description="呼吸音音频文件的存储路径")
    snr_db: Optional[float] = Field(None, description="信噪比（dB），可选扩展")
    low_quality: bool = Field(False, description="是否判定为录音质量过低（需重新录制）")

    model_config = ConfigDict(from_attributes=True)


class LungSoundUploadResponse(BaseModel):
    """上传接口响应：返回存储路径与推理结果，供前端即时展示并传入 LangGraph 会话。"""
    lung_sound_path: str = Field(..., description="已保存的音频路径，供后续传入诊断工作流")
    result: LungSoundResult = Field(..., description="呼吸音推理结果")
    message: str = Field("Lung sound analysis completed.", description="处理说明")