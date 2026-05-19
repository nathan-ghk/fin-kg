from langgraph.graph import StateGraph, END
from utils.schema import AgentState
from nodes import (
    supervisor_node, relational_db_node,
    graph_db_node, synthesizer_node
)

def route_decision(state: AgentState):
    return state.route  # "sql" or "graph"

def build_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("relational_db", relational_db_node)
    workflow.add_node("graph_db", graph_db_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {"sql": "relational_db", "graph": "graph_db"}
    )
    workflow.add_edge("relational_db", "synthesizer")
    workflow.add_edge("graph_db", "synthesizer")
    workflow.add_edge("synthesizer", END)
    return workflow.compile()

# ✨ 모듈 레벨에서 컴파일 → FastAPI에서 바로 import
agent_engine = build_agent()
