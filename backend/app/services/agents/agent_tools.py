"""
Agent Tools —— 把后端既有能力统一封装为可被模型动态调用的工具。

工具清单（全部通过 ToolRegistry 暴露给 ReAct loop）：
  - analyze_symptoms        症状结构化提取（Gemini 结构化输出）
  - analyze_lung_sound      呼吸音听诊（PBRNet GPU 推理）
  - analyze_medical_image   医学影像解读（Gemini Vision）
  - retrieve_medical_evidence  循证证据检索（本地 RAG + 外部可信源）
  - find_nearby_clinics     紧急情况下附近诊所检索
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.agents.harness import BaseTool, ToolRegistry
from app.services.llm.gemini_client import gemini_client
from app.services.lung_sound_service import lung_sound_service
from app.services.vision.gemini_vision import gemini_vision
from app.services.rag.grounding import retrieve_medical_grounding
from app.services.rag.source_catalog import retrieve_catalog_citations
from app.services.rag.reputable_sources import retrieve_reputable_citations
from app.services.agents.nodes.emergency_action import get_nearby_clinics
from app.services.agents.nodes.symptom_analyzer import SymptomExtraction


# ---------------------------------------------------------------------------
# 工具参数 Schema
# ---------------------------------------------------------------------------
class SymptomsArgs(BaseModel):
    symptoms: str = Field(..., description="患者主诉的原始描述")
    age: Optional[int] = Field(None, description="患者年龄")
    gender: Optional[str] = Field(None, description="患者性别")


class LungSoundArgs(BaseModel):
    audio_path: str = Field(..., description="呼吸音 wav 音频的绝对路径")


class ImageArgs(BaseModel):
    image_base64: str = Field(..., description="医学影像的 base64 编码")
    image_type: str = Field(..., description="影像类型：chest_xray/ct_scan/skin_lesion/mri 等")
    additional_context: Optional[str] = Field(None, description="附加的患者症状/病史上下文")


class EvidenceArgs(BaseModel):
    query: str = Field(..., description="用于检索循证医学证据的查询问题")


class ClinicsArgs(BaseModel):
    lat: float = Field(..., description="患者所在纬度")
    lng: float = Field(..., description="患者所在经度")
    limit: int = Field(3, ge=1, le=10, description="返回的诊所数量")


# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------
async def _analyze_symptoms(symptoms: str, age: Optional[int] = None,
                            gender: Optional[str] = None) -> Dict[str, Any]:
    patient_info = (
        f"Raw Symptoms: {symptoms}\n"
        f"Age: {age if age is not None else 'Unknown'}\n"
        f"Gender: {gender or 'Unknown'}"
    )
    system_prompt = f"""You are a specialized medical assistant. Convert raw patient
descriptions into structured clinical data for a doctor's review.

Patient Context:
{patient_info}

If a field is not mentioned, mark it 'unknown' or use an empty list."""
    extracted: SymptomExtraction = await gemini_client.generate_structured(
        prompt=system_prompt,
        response_model=SymptomExtraction,
    )
    return extracted.model_dump()


def _analyze_lung_sound(audio_path: str) -> Dict[str, Any]:
    """同步 GPU 推理（由 harness 丢线程池执行）。"""
    return lung_sound_service.analyze(audio_path)


async def _analyze_medical_image(image_base64: str, image_type: str,
                                 additional_context: Optional[str] = None) -> Dict[str, Any]:
    try:
        image_data = base64.b64decode(image_base64)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"invalid base64 image data: {exc}"}
    return await gemini_vision.analyze_medical_image(
        image_data, image_type, additional_context=additional_context,
    )


def _provider_weight(provider: str) -> float:
    weights = {
        "LocalRAG": 1.0,
        "PubMed": 0.95,
        "OpenFDA": 0.9,
        "MedlinePlus": 0.85,
        "ClinicalTrials": 0.8,
    }
    return weights.get(provider, 0.75)


def _rank_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = sorted(
        citations,
        key=lambda c: float(c.get("similarity", 0.0) or 0.0) * _provider_weight(str(c.get("provider") or "")),
        reverse=True,
    )
    for idx, citation in enumerate(ranked, start=1):
        citation["rank"] = idx
    return ranked


async def _retrieve_medical_evidence(query: str) -> List[Dict[str, Any]]:
    grounding, catalog, reputable = await asyncio.gather(
        retrieve_medical_grounding(query, top_k=3),
        retrieve_catalog_citations(query, top_k=3),
        retrieve_reputable_citations(query, top_k=4),
    )
    return _rank_citations([
        *(catalog or []),
        *(grounding or []),
        *(reputable or []),
    ])[:8]


def _find_nearby_clinics(lat: float, lng: float, limit: int = 3) -> List[Dict[str, Any]]:
    return get_nearby_clinics(lat=lat, lng=lng, limit=limit)


# ---------------------------------------------------------------------------
# 组装工具注册表
# ---------------------------------------------------------------------------
def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(BaseTool(
        name="analyze_symptoms",
        description="把患者的自由文本症状描述结构化，提取主要症状、持续时间、严重程度、诱因等临床字段。",
        args_schema=SymptomsArgs,
        coroutine=_analyze_symptoms,
    ))
    registry.register(BaseTool(
        name="analyze_lung_sound",
        description="对呼吸音 wav 音频做听诊分析，返回 normal/crackle/wheeze/both 四分类标签与置信度。需要提供音频文件路径。",
        args_schema=LungSoundArgs,
        func=_analyze_lung_sound,
    ))
    registry.register(BaseTool(
        name="analyze_medical_image",
        description="解读医学影像（胸片/CT/皮肤病灶/MRI），返回影像所见、严重程度与建议。需要 base64 影像与影像类型。",
        args_schema=ImageArgs,
        coroutine=_analyze_medical_image,
    ))
    registry.register(BaseTool(
        name="retrieve_medical_evidence",
        description="从本地知识库与可信外部来源检索循证医学证据/指南，返回带来源与排名的引文列表。",
        args_schema=EvidenceArgs,
        coroutine=_retrieve_medical_evidence,
    ))
    registry.register(BaseTool(
        name="find_nearby_clinics",
        description="根据经纬度检索附近社区医疗设施（用于紧急情况转诊）。",
        args_schema=ClinicsArgs,
        func=_find_nearby_clinics,
    ))
    return registry