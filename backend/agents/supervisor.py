"""Supervisor — routes an incoming request to the right agent node.

For v1 this is a thin dispatcher: the `request_type` set on AgentState by
main.py (one per FastAPI route) determines which single agent node runs.
It's built as a real LangGraph conditional edge rather than a Python
if/else buried in main.py, so it's straightforward to extend later — e.g.
letting the NPC agent decide mid-conversation that a hint is needed and
hand off to the Tutor agent without a new HTTP round trip, instead of
staying a strict one-request-type-to-one-node mapping forever.
"""

from typing import Literal

from .state import AgentState

AgentNode = Literal["tutor", "scenario", "npc"]

# Which agent node handles each request_type. "hint" and "explain" both
# route to the Tutor agent (see tutor_agent.tutor_node, which dispatches
# between them internally based on request_type).
_ROUTES: dict[str, AgentNode] = {
    "hint": "tutor",
    "explain": "tutor",
    "scenario": "scenario",
    "dialogue": "npc",
}


def route_request(state: AgentState) -> AgentNode:
    """Conditional-entry-point function for graph.py's
    `graph.set_conditional_entry_point(route_request)`. Must return one of
    the exact node names passed to `graph.add_node(...)` for that agent —
    see graph.py (Step 7)."""

    request_type = state.get("request_type")
    try:
        return _ROUTES[request_type]
    except KeyError:
        raise ValueError(
            f"No route configured for request_type={request_type!r}. "
            f"Known request types: {sorted(_ROUTES)}"
        )
