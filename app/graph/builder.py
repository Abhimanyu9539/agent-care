"""The workflow as a LangGraph flowchart: nodes are steps, edges say which step comes next.

For now it has one step. Later steps add the LLM safety check, routing and a coordinator.
"""

from langgraph.graph import END, START, StateGraph

from app.agents.safety.agent import safety_intake
from app.graph.state import RequestState


def build_graph():
    graph = StateGraph(RequestState)
    graph.add_node("safety_intake", safety_intake)

    graph.add_edge(START, "safety_intake")
    graph.add_edge("safety_intake", END)
    
    return graph.compile()


GRAPH = build_graph()
