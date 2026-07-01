"""
LangGraph StateGraph definition for the Weather & Outdoor Activity Planner
Deep Agent.

Graph topology:

    START
      |
      v
  intent_analysis_step
      |
      v
    decision_step  --(needs_clarification=True)--> clarify --> format_response --> END
        |
        +-----------(needs_weather=True)--------> fetch_weather --> analyze --> format_response --> END
      |
      +-----------(needs_weather=False)---> analyze --> format_response --> END
"""
from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.nodes import (
    clarification_node,
    decision_node,
    intent_analysis_node,
    reasoning_node,
    response_node,
    route_after_decision,
    weather_tool_node,
)
from app.state import AgentState

logger = logging.getLogger(__name__)


def build_graph():
    """Construct and compile the LangGraph StateGraph with memory checkpointing."""
    graph = StateGraph(AgentState)

    # Node names are suffixed with _step / _node to avoid clashing with
    # AgentState field names (LangGraph raises ValueError on collision).
    graph.add_node("intent_analysis_step", intent_analysis_node)
    graph.add_node("decision_step", decision_node)
    graph.add_node("clarify", clarification_node)
    graph.add_node("fetch_weather", weather_tool_node)
    graph.add_node("analyze", reasoning_node)
    graph.add_node("format_response", response_node)

    graph.add_edge(START, "intent_analysis_step")
    graph.add_edge("intent_analysis_step", "decision_step")

    graph.add_conditional_edges(
        "decision_step",
        route_after_decision,
        {
            "clarify": "clarify",
            "weather_tool": "fetch_weather",
            "reasoning": "analyze",
        },
    )

    graph.add_edge("clarify", "format_response")
    graph.add_edge("fetch_weather", "analyze")
    graph.add_edge("analyze", "format_response")
    graph.add_edge("format_response", END)

    # In-memory checkpointing keyed by thread/session id.
    # Swap MemorySaver for SqliteSaver / PostgresSaver in production
    # without touching graph topology.
    checkpointer = MemorySaver()

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("LangGraph Deep Agent graph compiled successfully.")
    return compiled


# Singleton compiled graph used by the FastAPI app.
agent_graph = build_graph()
