from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.services.agents.state import AgentState


def triage_router(state: AgentState) -> Literal["emergency_action", "image_analysis", "diagnosis"]:
    """Emergency bypass routing after symptom analysis."""
    if state.get("is_emergency"):
        return "emergency_action"
    if state.get("has_image"):
        return "image_analysis"
    return "diagnosis"


def route_lung_sound(state: AgentState) -> Literal["lung_sound_agent", "diagnosis"]:
    """条件动态路由：仅当存在呼吸音音频时才执行 lung_sound_agent，否则直接进入 diagnosis。
    无音频时跳过该节点，节省 GPU 与 token 开销。"""
    if state.get("lung_sound_path") or state.get("lung_sound_result"):
        return "lung_sound_agent"
    return "diagnosis"


async def lung_sound_gate_node(state: AgentState) -> AgentState:
    """轻量汇聚节点：将「图像分析」与「纯文本诊断」两条路径统一汇入呼吸音条件路由。"""
    return state


def create_medical_agent_graph():
    from app.services.agents.nodes.diagnostician import diagnostician_node
    from app.services.agents.nodes.emergency_action import emergency_action_node
    from app.services.agents.nodes.image_analyzer import image_analyzer_node
    from app.services.agents.nodes.lung_sound import lung_sound_agent_node
    from app.services.agents.nodes.report_generator import report_generator_node
    from app.services.agents.nodes.symptom_analyzer import symptom_analyzer_node
    from app.services.agents.nodes.treatment_planner import treatment_planner_node
    from app.services.agents.nodes.triage import triage_node

    workflow = StateGraph(AgentState)

    workflow.add_node("triage", triage_node)
    workflow.add_node("symptom_analysis", symptom_analyzer_node)
    workflow.add_node("emergency_action", emergency_action_node)
    workflow.add_node("image_analysis", image_analyzer_node)
    workflow.add_node("lung_sound_gate", lung_sound_gate_node)
    workflow.add_node("lung_sound_agent", lung_sound_agent_node)
    workflow.add_node("diagnosis", diagnostician_node)
    workflow.add_node("treatment_planning", treatment_planner_node)
    workflow.add_node("generate_report", report_generator_node)

    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "symptom_analysis")

    # symptom_analysis 的三路分支：diagnosis 出口改为先经 lung_sound_gate（呼吸音条件路由）。
    workflow.add_conditional_edges(
        "symptom_analysis",
        triage_router,
        {
            "emergency_action": "emergency_action",
            "image_analysis": "image_analysis",
            "diagnosis": "lung_sound_gate",
        },
    )

    # 图像分析完成后同样先经呼吸音条件路由。
    workflow.add_edge("image_analysis", "lung_sound_gate")
    workflow.add_conditional_edges(
        "lung_sound_gate",
        route_lung_sound,
        {
            "lung_sound_agent": "lung_sound_agent",
            "diagnosis": "diagnosis",
        },
    )
    workflow.add_edge("lung_sound_agent", "diagnosis")

    workflow.add_edge("diagnosis", "treatment_planning")
    workflow.add_edge("treatment_planning", "generate_report")
    workflow.add_edge("generate_report", END)
    workflow.add_edge("emergency_action", END)

    return workflow.compile()


_medical_agent_graph = None


def get_medical_agent_graph():
    global _medical_agent_graph
    if _medical_agent_graph is None:
        _medical_agent_graph = create_medical_agent_graph()
    return _medical_agent_graph