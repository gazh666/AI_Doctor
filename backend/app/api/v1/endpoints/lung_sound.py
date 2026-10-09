"""肺部呼吸音上传与分析端点。"""

import asyncio
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.deps import CurrentUser
from app.schemas.lung_sound import LungSoundResult, LungSoundUploadResponse
from app.services.lung_sound_service import MAX_UPLOAD_BYTES, lung_sound_service

logger = logging.getLogger(__name__)
router = APIRouter()

UNAUTHORIZED_RESPONSE = {
    401: {
        "description": "Not authenticated. Provide a valid Bearer access token.",
    }
}


@router.post(
    "/analyze",
    response_model=LungSoundUploadResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def analyze_lung_sound(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """接收肺部呼吸音 wav，保存并推理，返回标签/置信度/存储路径。"""

    filename = file.filename or ""
    if not filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="仅支持 .wav 格式的肺部呼吸音音频。")

    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="上传文件为空。")
    if len(audio_data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB）。",
        )

    try:
        saved_path = await asyncio.to_thread(lung_sound_service.save_audio, audio_data, filename)
        raw_result = await asyncio.to_thread(lung_sound_service.analyze, saved_path)
    except FileNotFoundError as e:
        logger.warning("呼吸音模型不可用：%s", e)
        raise HTTPException(status_code=503, detail=f"呼吸音模型暂不可用：{e}")
    except Exception:
        logger.exception("呼吸音分析失败")
        raise HTTPException(status_code=422, detail="音频无法解析或已损坏，请重新录制并上传。")

    result = LungSoundResult(**raw_result)
    return LungSoundUploadResponse(
        lung_sound_path=saved_path,
        result=result,
        message="肺部呼吸音分析完成（仅供辅助参考，不能替代医生诊断）。",
    )