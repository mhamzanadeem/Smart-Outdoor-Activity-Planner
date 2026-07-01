"""
LangGraph node implementations for the Weather & Outdoor Activity Planner
Deep Agent.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
import openai
import requests as _requests

from app.config import get_settings
from app.prompts import INTENT_ANALYSIS_SYSTEM_PROMPT, REASONING_SYSTEM_PROMPT
from app.state import AgentState
from app.tools import WeatherToolError, fetch_weather_data

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error classification helpers
# ---------------------------------------------------------------------------
_LLM_ERROR_MESSAGES = {
    "llm_auth_error": (
        "⚠️ LLM API key is invalid or missing. "
        "Please set a valid `LLM_API_KEY` in your `backend/.env` file "
        "and restart the server."
    ),
    "llm_rate_limit": (
        "⏱️ The LLM provider is rate-limiting requests. "
        "Please wait a moment and try again."
    ),
    "llm_unavailable": (
        "🔌 The LLM service is currently unreachable. "
        "Check your `LLM_API_BASE_URL` in `.env` or try again later."
    ),
}


def _classify_llm_error(exc: Exception) -> Tuple[str, str]:
    """Return (error_code, human_readable_message) for an LLM exception."""
    err_str = str(exc).lower()
    if isinstance(exc, openai.AuthenticationError) or "401" in err_str or "invalid api key" in err_str:
        return "llm_auth_error", _LLM_ERROR_MESSAGES["llm_auth_error"]
    if isinstance(exc, openai.RateLimitError) or "429" in err_str or "rate limit" in err_str:
        return "llm_rate_limit", _LLM_ERROR_MESSAGES["llm_rate_limit"]
    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
        return "llm_unavailable", _LLM_ERROR_MESSAGES["llm_unavailable"]
    return "llm_unavailable", _LLM_ERROR_MESSAGES["llm_unavailable"]

DEFAULT_CITY = "Rawalpindi"
VALID_TIMEFRAMES = {"current", "today", "tomorrow", "1 day after", "3 days after"}


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

    error_code: str | None = None
    error: str | None = None

    try:
        response = llm.invoke(messages)
        parsed = _safe_json_parse(response.content)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Intent analysis LLM call failed: %s", exc)
        error_code, error = _classify_llm_error(exc)
        parsed = {}

    intent = parsed.get("intent") or "general_weather"
    needs_weather = bool(parsed.get("needs_weather", True))
    extracted_city = (parsed.get("city") or "").strip()
    extracted_timeframe = parsed.get("timeframe")
    if extracted_timeframe not in VALID_TIMEFRAMES:
        extracted_timeframe = None
    activity = parsed.get("activity") or None

    user_query_lc = state["user_query"].lower()
    affirmative_heuristic = bool(
        re.search(r"\b(yes|yep|yeah|correct|confirmed|confirm|right|sure|ok|okay)\b", user_query_lc)
    )
    rejection_heuristic = bool(
        re.search(r"\b(no|wrong|incorrect|change|not\s+that|different)\b", user_query_lc)
    )

    is_confirmation = bool(parsed.get("is_confirmation", False) or affirmative_heuristic)
    is_rejection = bool(parsed.get("is_rejection", False) or rejection_heuristic)

    previous_proposed_city = state.get("proposed_city")
    previous_proposed_timeframe = state.get("proposed_timeframe")
    previous_confirmed_city = state.get("confirmed_city")
    previous_confirmed_timeframe = state.get("confirmed_timeframe")
    awaiting_confirmation = bool(state.get("awaiting_confirmation", False))

    proposed_city = extracted_city or previous_proposed_city
    proposed_timeframe = extracted_timeframe or previous_proposed_timeframe

    confirmed_city = previous_confirmed_city
    confirmed_timeframe = previous_confirmed_timeframe

    if is_rejection:
        confirmed_city = None
        confirmed_timeframe = None

    can_confirm_slots = bool(proposed_city and proposed_timeframe)
    if can_confirm_slots and (
        (awaiting_confirmation and is_confirmation and not is_rejection)
        or (is_confirmation and extracted_city and extracted_timeframe and not is_rejection)
    ):
        confirmed_city = proposed_city
        confirmed_timeframe = proposed_timeframe

    if confirmed_city and confirmed_timeframe:
        city = confirmed_city
        timeframe = confirmed_timeframe
        needs_clarification = False
        awaiting_confirmation = False
    else:
        city = proposed_city or ""
        timeframe = proposed_timeframe
        needs_clarification = bool(needs_weather)
        awaiting_confirmation = bool(needs_weather)

    logger.info(
        "[intent_analysis_node] intent=%s needs_weather=%s city=%s timeframe=%s activity=%s confirmed_city=%s confirmed_timeframe=%s",
        intent,
        needs_weather,
        city,
        timeframe,
        activity,
        confirmed_city,
        confirmed_timeframe,
    )

    return {
        "intent": intent,
        "needs_weather": needs_weather,
        "city": city,
        "timeframe": timeframe,
        "activity": activity,
        "proposed_city": proposed_city,
        "proposed_timeframe": proposed_timeframe,
        "confirmed_city": confirmed_city,
        "confirmed_timeframe": confirmed_timeframe,
        "awaiting_confirmation": awaiting_confirmation,
        "needs_clarification": needs_clarification,
        "tool_called": False,
        "tool_executions": [],
        "error_code": error_code,
        "error": error,
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
    if state.get("needs_clarification", False):
        return "clarify"
    return "weather_tool" if state.get("needs_weather", True) else "reasoning"


def clarification_node(state: AgentState) -> AgentState:
    """Ask clarifying questions until city and timeframe are explicitly confirmed."""
    proposed_city = state.get("proposed_city")
    proposed_timeframe = state.get("proposed_timeframe")

    if not proposed_city and not proposed_timeframe:
        message = (
            "Please confirm both details before I fetch weather:\n"
            "1) Which location (city) do you want?\n"
            "2) Which timeframe: current, today, tomorrow, 1 day after, or 3 days after?"
        )
    elif proposed_city and not proposed_timeframe:
        message = (
            f"I have location as '{proposed_city}'. Please confirm the timeframe: "
            "current, today, tomorrow, 1 day after, or 3 days after."
        )
    elif not proposed_city and proposed_timeframe:
        message = (
            f"I have timeframe as '{proposed_timeframe}'. Please confirm the location (city)."
        )
    else:
        message = (
            "Please confirm these details so I can continue:\n"
            f"Location: {proposed_city}\n"
            f"Timeframe: {proposed_timeframe}\n"
            "Reply with 'yes' to confirm, or send corrected values."
        )

    return {
        "reasoning": "",
        "final_answer": message,
        "tool_called": False,
        "weather_data": None,
    }


# ---------------------------------------------------------------------------
# Node 3: Weather Tool Node
# ---------------------------------------------------------------------------
def weather_tool_node(state: AgentState) -> AgentState:
    """Invoke the weather tool and record the execution for transparency."""
    city = state.get("confirmed_city") or state.get("city") or DEFAULT_CITY
    timeframe = state.get("confirmed_timeframe") or state.get("timeframe") or "current"
    logger.info("[weather_tool_node] fetching weather for city=%s timeframe=%s", city, timeframe)

    start = time.perf_counter()
    execution_record: dict = {
        "tool_name": "get_weather",
        "input": {"city": city, "timeframe": timeframe},
    }

    error_code: str | None = None
    error: str | None = None

    try:
        weather_data = fetch_weather_data(city, timeframe=timeframe)
        execution_record["output"] = weather_data
        execution_record["status"] = "success"
    except WeatherToolError as exc:
        logger.warning("[weather_tool_node] weather tool error: %s", exc)
        weather_data = None
        execution_record["output"] = {"error": str(exc)}
        execution_record["status"] = "error"
        err_str = str(exc).lower()
        if "not configured" in err_str or "weather_api_key" in err_str:
            error_code = "weather_api_missing"
            error = (
                "⚠️ Weather API key is missing. "
                "Please set `WEATHER_API_KEY` in your `backend/.env` file "
                "and restart the server."
            )
        elif "not found" in err_str:
            error_code = "weather_city_not_found"
            error = f"🔍 Could not find weather data for '{city}'. Try a different city name."
        else:
            error_code = "weather_fetch_error"
            error = f"🌐 Weather data unavailable: {exc}"
    except _requests.exceptions.ConnectionError:
        logger.exception("[weather_tool_node] network error fetching weather")
        weather_data = None
        execution_record["output"] = {"error": "Network error."}
        execution_record["status"] = "error"
        error_code = "weather_network_error"
        error = "🌐 Could not reach the weather provider. Check your internet connection."
    except Exception as exc:  # noqa: BLE001
        logger.exception("[weather_tool_node] unexpected error: %s", exc)
        weather_data = None
        execution_record["output"] = {"error": "Unexpected error fetching weather data."}
        execution_record["status"] = "error"
        error_code = "weather_fetch_error"
        error = "🌐 An unexpected error occurred fetching weather data. Please try again."

    execution_record["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)

    return {
        "tool_called": True,
        "tool_executions": [execution_record],
        "weather_data": weather_data,
        "city": city,
        "timeframe": timeframe,
        "error": error,
        "error_code": error_code,
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
Timeframe: {state.get('timeframe') or 'current'}

Weather data:
{weather_summary}
"""

    messages = [
        ("system", REASONING_SYSTEM_PROMPT),
        ("human", user_prompt),
    ]

    # If a critical error happened upstream (e.g. auth), skip LLM and propagate it
    upstream_error_code = state.get("error_code")
    if upstream_error_code in ("llm_auth_error", "llm_rate_limit", "llm_unavailable"):
        logger.warning("[reasoning_node] skipping LLM call due to upstream error: %s", upstream_error_code)
        return {
            "reasoning": "",
            "final_answer": "",
        }

    try:
        response = llm.invoke(messages)
        parsed = _safe_json_parse(response.content)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reasoning LLM call failed: %s", exc)
        error_code, error_msg = _classify_llm_error(exc)
        return {
            "reasoning": "",
            "final_answer": "",
            "error_code": error_code,
            "error": error_msg,
        }

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
