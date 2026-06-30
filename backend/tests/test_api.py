"""
Tests for the FastAPI /chat and /health endpoints.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_mock_graph_result(
    final_answer: str = "Yes, it is safe to cycle today!",
    reasoning: str = "Wind speed is low and rain probability is minimal.",
    tool_called: bool = True,
    weather_data: dict | None = None,
    intent: str = "activity_planning",
    city: str = "Rawalpindi",
):
    if weather_data is None:
        weather_data = {
            "city": "Rawalpindi",
            "temperature_c": 26.0,
            "feels_like_c": 27.0,
            "humidity_percent": 50.0,
            "wind_speed_kmh": 12.0,
            "visibility_km": 10.0,
            "condition": "Clear",
            "description": "clear sky",
            "rain_probability_percent": 8.0,
            "is_daytime": True,
        }
    return {
        "final_answer": final_answer,
        "reasoning": reasoning,
        "tool_called": tool_called,
        "tool_executions": [
            {
                "tool_name": "get_weather",
                "input": {"city": city},
                "output": weather_data,
                "status": "success",
                "duration_ms": 120.5,
            }
        ],
        "weather_data": weather_data,
        "intent": intent,
        "city": city,
    }


@pytest.fixture
def mock_agent_graph():
    with patch("app.routes.agent_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=make_mock_graph_result())
        yield mock_graph


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_env" in data


def test_chat_endpoint_success(mock_agent_graph):
    payload = {"message": "Can I go cycling this evening?"}
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["final_answer"] == "Yes, it is safe to cycle today!"
    assert data["tool_called"] is True
    assert len(data["tool_executions"]) == 1
    assert data["tool_executions"][0]["tool_name"] == "get_weather"
    assert data["weather_data"] is not None
    assert data["weather_data"]["city"] == "Rawalpindi"
    assert "session_id" in data
    assert data["user_query"] == "Can I go cycling this evening?"


def test_chat_endpoint_with_session_id(mock_agent_graph):
    payload = {"message": "Will it rain today?", "session_id": "test-session-abc"}
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-abc"


def test_chat_endpoint_empty_message():
    payload = {"message": ""}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422


def test_chat_endpoint_message_too_long():
    payload = {"message": "a" * 2001}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422


def test_chat_endpoint_agent_error(mock_agent_graph):
    mock_agent_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM timeout"))
    payload = {"message": "Is it safe to drive tonight?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 500
    assert "Agent failed" in response.json()["detail"]


def test_chat_endpoint_no_tool_called(mock_agent_graph):
    mock_agent_graph.ainvoke = AsyncMock(
        return_value=make_mock_graph_result(tool_called=False, weather_data=None)
    )
    payload = {"message": "Hello"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tool_called"] is False
