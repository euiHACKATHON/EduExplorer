"""Compiled LangGraph supervisor for all generative game routes."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .npc_agent import npc_node
from .scenario_agent import scenario_node
from .state import AgentState
from .supervisor import route_request
from .tutor_agent import tutor_node


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("tutor", tutor_node)
    workflow.add_node("scenario", scenario_node)
    workflow.add_node("npc", npc_node)
    workflow.add_conditional_edges(
        START,
        route_request,
        {"tutor": "tutor", "scenario": "scenario", "npc": "npc"},
    )
    workflow.add_edge("tutor", END)
    workflow.add_edge("scenario", END)
    workflow.add_edge("npc", END)
    return workflow.compile(checkpointer=MemorySaver())


compiled = build_graph()


async def run_agent(state: AgentState, thread_id: str) -> AgentState:
    """Run one request while restoring prior NPC conversation history."""

    config = {"configurable": {"thread_id": thread_id}}
    if state.get("request_type") == "dialogue":
        snapshot = await compiled.aget_state(config)
        history = snapshot.values.get("conversation_history", [])
        if history and not state.get("conversation_history"):
            state["conversation_history"] = history
    return await compiled.ainvoke(state, config)
