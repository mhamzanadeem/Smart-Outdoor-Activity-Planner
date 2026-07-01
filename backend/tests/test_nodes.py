"""
Tests for individual LangGraph nodes.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app import nodes


class FakeAIMessage:
    def __init__(self, content: str):
        self.content = content


def test_route_after_decision_weather_needed():
    state = {"needs_weather": True, "needs_clarification": False}
    assert nodes.route_after_decision(state) == "weather_tool"


def test_route_after_decision_weather_not_needed():
    state = {"needs_weather": False}
    assert nodes.route_after_decision(state) == "reasoning"


def test_route_after_decision_clarify():
    state = {"needs_weather": True, "needs_clarification": True}
    assert nodes.route_after_decision(state) == "clarify"


def test_intent_analysis_node(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "intent": "sports_feasibility",
                "needs_weather": True,
                "city": "Lahore",
                "timeframe": "tomorrow",
                "activity": "cricket",
            }
        )
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {"user_query": "Can I play cricket tomorrow in Lahore?"}
    result = nodes.intent_analysis_node(state)

    assert result["intent"] == "sports_feasibility"
    assert result["needs_weather"] is True
    assert result["city"] == "Lahore"
    assert result["timeframe"] == "tomorrow"
    assert result["activity"] == "cricket"
    assert result["needs_clarification"] is True


def test_intent_analysis_node_defaults_on_bad_json(monkeypatch):
    fake_response = FakeAIMessage("not valid json")
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {"user_query": "Should I carry an umbrella?"}
    result = nodes.intent_analysis_node(state)

    assert result["intent"] == "general_weather"
    assert result["city"] == ""


def test_intent_analysis_confirms_slots_on_yes(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "intent": "general_weather",
                "needs_weather": True,
                "city": "",
                "timeframe": None,
                "activity": None,
                "is_confirmation": True,
                "is_rejection": False,
            }
        )
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {
        "user_query": "yes",
        "awaiting_confirmation": True,
        "proposed_city": "Lahore",
        "proposed_timeframe": "tomorrow",
    }
    result = nodes.intent_analysis_node(state)

    assert result["confirmed_city"] == "Lahore"
    assert result["confirmed_timeframe"] == "tomorrow"
    assert result["needs_weather"] is True
    assert result["needs_clarification"] is False


def test_intent_analysis_yes_keeps_pending_weather_even_if_llm_says_false(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "intent": "general_information",
                "needs_weather": False,
                "city": "",
                "timeframe": None,
                "activity": None,
                "is_confirmation": True,
                "is_rejection": False,
            }
        )
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {
        "user_query": "yes",
        "awaiting_confirmation": True,
        "proposed_city": "Hunza Valley",
        "proposed_timeframe": "3 days after",
    }
    result = nodes.intent_analysis_node(state)

    assert result["needs_weather"] is True
    assert result["confirmed_city"] == "Hunza Valley"
    assert result["confirmed_timeframe"] == "3 days after"
    assert result["needs_clarification"] is False


def test_intent_analysis_new_city_overrides_previous_confirmed_city(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "intent": "general_weather",
                "needs_weather": True,
                "city": "Hunza",
                "timeframe": "3 days after",
                "activity": None,
                "is_confirmation": False,
                "is_rejection": False,
            }
        )
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {
        "user_query": "is weather good in hunza for next 3 days",
        "confirmed_city": "Hunza Valley",
        "confirmed_timeframe": "3 days after",
        "proposed_city": "Hunza Valley",
        "proposed_timeframe": "3 days after",
        "awaiting_confirmation": False,
    }
    result = nodes.intent_analysis_node(state)

    assert result["confirmed_city"] is None
    assert result["proposed_city"] == "Hunza"
    assert result["city"] == "Hunza"
    assert result["needs_clarification"] is True


def test_intent_analysis_non_weather_forces_no_weather(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "intent": "general_information",
                "needs_weather": True,
                "city": "Islamabad",
                "timeframe": "tomorrow",
                "activity": None,
            }
        )
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {"user_query": "Who is president of Pakistan?"}
    result = nodes.intent_analysis_node(state)

    assert result["needs_weather"] is False
    assert result["needs_clarification"] is False
    assert result["weather_data"] is None
    assert result["city"] == ""
    assert result["timeframe"] is None


def test_clarification_node_prompts_for_confirmation():
    state = {"proposed_city": "Karachi", "proposed_timeframe": "today"}
    result = nodes.clarification_node(state)

    assert "Please confirm" in result["final_answer"]
    assert "Karachi" in result["final_answer"]
    assert "today" in result["final_answer"]


def test_weather_tool_node_success(monkeypatch):
    fake_weather = {"city": "Rawalpindi", "temperature_c": 30.0}
    monkeypatch.setattr(nodes, "fetch_weather_data", lambda city, timeframe="current": fake_weather)

    state = {"confirmed_city": "Rawalpindi", "confirmed_timeframe": "tomorrow"}
    result = nodes.weather_tool_node(state)

    assert result["tool_called"] is True
    assert result["weather_data"] == fake_weather
    assert result["tool_executions"][0]["status"] == "success"
    assert result["tool_executions"][0]["input"]["timeframe"] == "tomorrow"


def test_weather_tool_node_handles_error(monkeypatch):
    def raise_error(city, timeframe="current"):
        raise nodes.WeatherToolError("city not found")

    monkeypatch.setattr(nodes, "fetch_weather_data", raise_error)

    state = {"city": "FakeCity"}
    result = nodes.weather_tool_node(state)

    assert result["tool_called"] is True
    assert result["weather_data"] is None
    assert result["tool_executions"][0]["status"] == "error"
    assert "Could not find weather data for" in result["error"]


def test_reasoning_node(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "reasoning": "Wind is low and rain probability is low, so conditions are favorable.",
                "final_answer": "Yes, you can play cricket tomorrow!",
            }
        )
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {
        "user_query": "Can I play cricket tomorrow?",
        "intent": "sports_feasibility",
        "activity": "cricket",
        "city": "Lahore",
        "weather_data": {"temperature_c": 28, "wind_speed_kmh": 10, "rain_probability_percent": 5},
    }
    result = nodes.reasoning_node(state)

    assert "favorable" in result["reasoning"]
    assert "Yes" in result["final_answer"]


def test_reasoning_node_general_query_skips_weather_prompt(monkeypatch):
    fake_response = FakeAIMessage("As of now, the President of Pakistan is Asif Ali Zardari.")
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {
        "user_query": "Who is president of Pakistan?",
        "needs_weather": False,
        "weather_data": {"city": "Islamabad", "temperature_c": 33},
    }
    result = nodes.reasoning_node(state)

    assert "President of Pakistan" in result["final_answer"]
    assert result["weather_data"] is None


def test_response_node():
    state = {"final_answer": "You should carry an umbrella today."}
    result = nodes.response_node(state)
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "You should carry an umbrella today."
