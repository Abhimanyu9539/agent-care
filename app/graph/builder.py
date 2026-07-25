"""The workflow as a LangGraph flowchart: nodes are steps, edges say which step comes next.

Safety runs first. Only an ordinary (ADMIN) request goes on to routing; anything else stops after safety.
Each run gets a WorkflowContext (settings and a database session), so nodes can reach the LLM and the tools.
"""

from langgraph.graph import END, START, StateGraph

from app.agents.routing.agent import route_request
from app.agents.safety.agent import safety_intake
from app.graph.state import RequestState, WorkflowContext


def after_safety(state: RequestState) -> str:
    return "route_request" if state["safety"]["category"] == "ADMIN" else END


def build_graph():
    graph = StateGraph(RequestState, context_schema=WorkflowContext)
    graph.add_node("safety_intake", safety_intake)
    graph.add_node("route_request", route_request)

    graph.add_edge(START, "safety_intake")
    graph.add_conditional_edges("safety_intake", after_safety, ["route_request", END])
    graph.add_edge("route_request", END)

    return graph.compile()


GRAPH = build_graph()
