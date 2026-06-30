"""
LangGraph node implementations for the Weather & Outdoor Activity Planner
Deep Agent.
"""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.prompts import INTENT_ANALYSIS_SYSTEM_PROMPT, REASONING_SYSTEM_PROMPT
from app.state import AgentState
from app.tools import WeatherToolError, fetch_weather_data

logger = logging.getLogger(__name__)

DEFAULT_CITY = "Rawalpindi"


def _get_llm(temperature: float | None = None) -> ChatOpenAI:
    """
    Build an LLM client pointed at an OpenAI-compatible, open-source model
    endpoint (e.g. Groq, Together AI, vLLM, Ollama-compatible gateway).
    Explicitly NOT using OpenAI's own API/models.
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model_name,
        api_key=settings.llm_api_key or "not-set",
        base_url=settings.llm_api_base_url,
        temperature=temperature if temperature is not None else settings.llm_temperature,
        timeout=settings.request_timeout_seconds,
    )


def _safe_json_parse(raw_text: str) -> dict:
    """Parse JSON from an LLM response, tolerating markdown code fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from LLM output: %s", raw_text)
        return {}


# ---------------------------------------------------------------------------
# Node 1: Intent Analysis
# ---------------------------------------------------------------------------
def intent_analysis_node(state: AgentState) -> AgentState:
    """Analyze the user's message to determine intent, city, and activity."""
    logger.info("[intent_analysis_node] analyzing query: %s", state["user_query"])
    llm = _get_llm(temperature=0.0)

    messages = [
        ("system", INTENT_ANALYSIS_SYSTEM_PROMPT),
        ("human", state["user_query"]),
    ]

    try:
        response = llm.invoke(messages)
        parsed = _safe_json_parse(response.content)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Intent analysis LLM call failed: %s", exc)
        parsed = {}

    intent = parsed.get("intent") or "general_weather"
    needs_weather = bool(parsed.get("needs_weather", True))
    city = (parsed.get("city") or "").strip() or DEFAULT_CITY
    activity = parsed.get("activity") or None

    logger.info(
        "[intent_analysis_node] intent=%s needs_weather=%s city=%s activity=%s",
        intent,
        needs_weather,
        city,
        activity,
    )

    return {
        "intent": intent,
        "needs_weather": needs_weather,
        "city": city,
        "activity": activity,
        "tool_called": False,
        "tool_executions": [],
    }


# ---------------------------------------------------------------------------
# Node 2: Decision Node (routing only — implemented as conditional edge logic
# in graph.py, this node simply logs/normalizes the decision state)
# ---------------------------------------------------------------------------
def decision_node(state: AgentState) -> AgentState:
    """Decide whether the weather tool must be invoked."""
    needs_weather = state.get("needs_weather", True)
    logger.info("[decision_node] needs_weather=%s", needs_weather)
    return {}


def route_after_decision(state: AgentState) -> str:
    """Conditional routing function used by the StateGraph."""
    return "weather_tool" if state.get("needs_weather", True) else "reasoning"


# ---------------------------------------------------------------------------
# Node 3: Weather Tool Node
# ---------------------------------------------------------------------------
def weather_tool_node(state: AgentState) -> AgentState:
    """Invoke the weather tool and record the execution for transparency."""
    city = state.get("city") or DEFAULT_CITY
    logger.info("[weather_tool_node] fetching weather for city=%s", city)

    start = time.perf_counter()
    execution_record: dict = {
        "tool_name": "get_weather",
        "input": {"city": city},
    }

    try:
        weather_data = fetch_weather_data(city)
        execution_record["output"] = weather_data
        execution_record["status"] = "success"
        error = None
    except WeatherToolError as exc:
        logger.warning("[weather_tool_node] weather tool error: %s", exc)
        weather_data = None
        execution_record["output"] = {"error": str(exc)}
        execution_record["status"] = "error"
        error = str(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[weather_tool_node] unexpected error: %s", exc)
        weather_data = None
        execution_record["output"] = {"error": "Unexpected error fetching weather data."}
        execution_record["status"] = "error"
        error = "Unexpected error fetching weather data."

    execution_record["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)

    return {
        "tool_called": True,
        "tool_executions": [execution_record],
        "weather_data": weather_data,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Node 4: Reasoning Node
# ---------------------------------------------------------------------------
def reasoning_node(state: AgentState) -> AgentState:
    """Reason over weather data + intent to produce structured insight."""
    logger.info("[reasoning_node] generating reasoning + answer")
    llm = _get_llm()

    weather_data = state.get("weather_data")
    weather_summary = (
        json.dumps(weather_data, indent=2) if weather_data else "No weather data available."
    )

    user_prompt = f"""
User question: {state['user_query']}
Detected intent: {state.get('intent', 'general_weather')}
Detected activity: {state.get('activity') or 'none specified'}
City: {state.get('city', DEFAULT_CITY)}

Weather data:
{weather_summary}
"""

    messages = [
        ("system", REASONING_SYSTEM_PROMPT),
        ("human", user_prompt),
    ]

    try:
        response = llm.invoke(messages)
        parsed = _safe_json_parse(response.content)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reasoning LLM call failed: %s", exc)
        parsed = {}

    reasoning = parsed.get("reasoning") or (
        "I attempted to reason about your request, but encountered an issue "
        "generating detailed reasoning. Here is a best-effort answer based on "
        "available data."
    )
    final_answer = parsed.get("final_answer") or (
        "I'm having trouble generating a complete answer right now. Please "
        "try rephrasing your question or try again shortly."
    )

    return {
        "reasoning": reasoning,
        "final_answer": final_answer,
    }


# ---------------------------------------------------------------------------
# Node 5: Response Node
# ---------------------------------------------------------------------------
def response_node(state: AgentState) -> AgentState:
    """Finalize the structured response and append it to message history."""
    final_answer = state.get("final_answer", "")
    logger.info("[response_node] finalizing response")
    return {
        "messages": [AIMessage(content=final_answer)],
    }
