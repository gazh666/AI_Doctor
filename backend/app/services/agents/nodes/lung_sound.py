"""
Lung Sound Agent Node
呼吸音分析节点：作为独立 Agent 接入 LangGraph 工作流。

职责：当 state 中存在 lung_sound_path 时执行呼吸音分析；
若已有分析结果则直接复用，避免重复 GPU 推理。
"""
from app.services.agents.state import AgentState
from app.services.lung_sound_service import lung_sound_service


async def lung_sound_agent_node(state: AgentState) -> AgentState:
    existing = state.get("lung_sound_result")
    path = state.get("lung_sound_path")

    # 已有结果（随 state 传入）：直接复用，跳过重复推理以节省 GPU。
    if existing:
        return {
            **state,
            "lung_sound_result": existing,
            "next_step": "diagnosis",
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        f"🫁 **Lung Sound Auscultation**\n"
                        f"- Label: {existing.get('label', 'unknown')}\n"
                        f"- Confidence: {existing.get('confidence', 0):.0%}"
                    ),
                }
            ],
        }

    if not path:
        return {**state, "next_step": "diagnosis"}

    try:
        result = lung_sound_service.analyze(path)
    except Exception as e:  # noqa: BLE001
        # 推理失败或音频损坏：不崩溃工作流，继续文本诊断。
        return {
            **state,
            "next_step": "diagnosis",
            "messages": [
                {
                    "role": "assistant",
                    "content": "⚠️ 呼吸音分析失败，将继续基于文本症状进行诊断。",
                }
            ],
        }

    label = result.get("label", "unknown")
    confidence = float(result.get("confidence", 0.0))
    reliability = "" if confidence >= 0.7 else "（听诊可信度低，建议临床医生复核）"

    return {
        **state,
        "lung_sound_result": result,
        "next_step": "diagnosis",
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"🫁 **Lung Sound Auscultation**\n"
                    f"- Label: {label}\n"
                    f"- Confidence: {confidence:.0%}{reliability}"
                ),
            }
        ],
    }