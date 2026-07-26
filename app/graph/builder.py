"""The workflow as a LangGraph flowchart: nodes are steps, edges say which step comes next.

Safety runs first; only an ordinary (ADMIN) request goes on to the coordinator. The coordinator is the hub:
it hands the request to one agent at a time, and every agent reports back to it, until it finishes.
Each run gets a WorkflowContext (settings and a database session), so nodes can reach the LLM and the tools.
Draw it as a PNG with `python -m app.graph.builder` (writes workflow_graph.png next to this file).
"""

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agents.coordinator.agent import coordinate
from app.agents.routing.agent import route_request
from app.agents.safety.agent import safety_intake
from app.graph.state import RequestState, WorkflowContext

# The agents the coordinator can hand a request to, and their graph nodes.
WORKERS = {"routing": "route_request"}


def after_safety(state: RequestState) -> str:
    return "coordinator" if state["safety"]["category"] == "ADMIN" else END


def after_coordinator(state: RequestState) -> str:
    return WORKERS.get(state["next_agent"], END)  # "finish" ends the run


def build_graph():
    graph = StateGraph(RequestState, context_schema=WorkflowContext)
    graph.add_node("safety_intake", safety_intake)
    graph.add_node("coordinator", coordinate)
    graph.add_node("route_request", route_request)

    graph.add_edge(START, "safety_intake")
    graph.add_conditional_edges("safety_intake", after_safety, ["coordinator", END])
    graph.add_conditional_edges("coordinator", after_coordinator, [*WORKERS.values(), END])
    for node in WORKERS.values():
        graph.add_edge(node, "coordinator")  # every agent reports back to the coordinator

    return graph.compile()


GRAPH = build_graph()


if __name__ == "__main__":
    # Rendered by the mermaid.ink web service (LangGraph's default); only node names are sent.
    png_file = Path(__file__).parent / "workflow_graph.png"
    GRAPH.get_graph().draw_mermaid_png(output_file_path=str(png_file))
    print(f"Wrote {png_file}")
