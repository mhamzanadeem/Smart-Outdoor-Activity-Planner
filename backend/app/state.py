"""
Typed state definitions for the LangGraph Deep Agent.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class ToolExecutionRecord(TypedDict, total=False):
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    status: str
    duration_ms: float | None


class AgentState(TypedDict, total=False):
    """
    Shared, typed state threaded through every node of the graph.
    """

    # Conversation memory (append-only via reducer)
    messages: Annotated[list[BaseMessage], operator.add]

    # Raw user input for this turn
    user_query: str
    session_id: str

    # Intent analysis output
    intent: str
    needs_weather: bool
    city: str
    cities: list[str]
    timeframe: str | None
    activity: str | None

    # Confirmed slots across turns
    confirmed_city: str | None
    confirmed_cities: list[str]
    confirmed_timeframe: str | None
    proposed_city: str | None
    proposed_cities: list[str]
    proposed_timeframe: str | None
    awaiting_confirmation: bool
    needs_clarification: bool

    # Tool execution
    tool_called: bool
    tool_executions: Annotated[list[ToolExecutionRecord], operator.add]
    weather_data: dict[str, Any] | None
    weather_data_list: list[dict[str, Any]]

    # Reasoning + final structured output
    reasoning: str
    final_answer: str

    # Error tracking — error_code is a machine-readable category for the frontend
    error: str | None
    error_code: str | None
