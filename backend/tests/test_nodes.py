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
    state = {"needs_weather": True}
    assert nodes.route_after_decision(state) == "weather_tool"


def test_route_after_decision_weather_not_needed():
    state = {"needs_weather": False}
    assert nodes.route_after_decision(state) == "reasoning"


def test_intent_analysis_node(monkeypatch):
    fake_response = FakeAIMessage(
        json.dumps(
            {
                "intent": "sports_feasibility",
                "needs_weather": True,
                "city": "Lahore",
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
    assert result["activity"] == "cricket"


def test_intent_analysis_node_defaults_on_bad_json(monkeypatch):
    fake_response = FakeAIMessage("not valid json")
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response
    monkeypatch.setattr(nodes, "_get_llm", lambda temperature=None: fake_llm)

    state = {"user_query": "Should I carry an umbrella?"}
    result = nodes.intent_analysis_node(state)

    assert result["intent"] == "general_weather"
    assert result["city"] == nodes.DEFAULT_CITY


def test_weather_tool_node_success(monkeypatch):
    fake_weather = {"city": "Rawalpindi", "temperature_c": 30.0}
    monkeypatch.setattr(nodes, "fetch_weather_data", lambda city: fake_weather)

    state = {"city": "Rawalpindi"}
    result = nodes.weather_tool_node(state)

    assert result["tool_called"] is True
    assert result["weather_data"] == fake_weather
    assert result["tool_executions"][0]["status"] == "success"


def test_weather_tool_node_handles_error(monkeypatch):
    def raise_error(city):
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


def test_response_node():
    state = {"final_answer": "You should carry an umbrella today."}
    result = nodes.response_node(state)
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "You should carry an umbrella today."
