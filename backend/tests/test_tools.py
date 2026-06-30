"""
Tests for the Weather Tool.
"""
from __future__ import annotations

import pytest

from app import tools


@pytest.fixture
def mock_current_weather_response():
    return {
        "name": "Rawalpindi",
        "main": {"temp": 28.5, "feels_like": 30.1, "humidity": 55},
        "wind": {"speed": 4.2},
        "weather": [{"main": "Clear", "description": "clear sky"}],
        "visibility": 10000,
        "sys": {"sunrise": 1000, "sunset": 50000},
        "dt": 20000,
    }


@pytest.fixture
def mock_forecast_response():
    return {
        "list": [
            {"pop": 0.1},
            {"pop": 0.2},
            {"pop": 0.15},
            {"pop": 0.05},
        ]
    }


def test_kmh_from_ms():
    assert tools._kmh_from_ms(10) == 36.0
    assert tools._kmh_from_ms(0) == 0.0


def test_fetch_weather_data_success(monkeypatch, mock_current_weather_response, mock_forecast_response):
    monkeypatch.setattr(tools, "_fetch_current_weather", lambda city: mock_current_weather_response)
    monkeypatch.setattr(tools, "_fetch_rain_probability", lambda city: 12.5)

    result = tools.fetch_weather_data("Rawalpindi")

    assert result["city"] == "Rawalpindi"
    assert result["temperature_c"] == 28.5
    assert result["humidity_percent"] == 55
    assert result["wind_speed_kmh"] == pytest.approx(15.1, abs=0.5)
    assert result["condition"] == "Clear"
    assert result["rain_probability_percent"] == 12.5
    assert result["is_daytime"] is True


def test_fetch_weather_data_city_not_found(monkeypatch):
    def raise_error(city):
        raise tools.WeatherToolError(f"City '{city}' was not found by the weather provider.")

    monkeypatch.setattr(tools, "_fetch_current_weather", raise_error)

    with pytest.raises(tools.WeatherToolError):
        tools.fetch_weather_data("NotARealCity12345")


def test_get_weather_tool_invocation(monkeypatch, mock_current_weather_response):
    monkeypatch.setattr(tools, "_fetch_current_weather", lambda city: mock_current_weather_response)
    monkeypatch.setattr(tools, "_fetch_rain_probability", lambda city: 5.0)

    result = tools.get_weather_tool.invoke({"city": "Rawalpindi"})
    assert result["city"] == "Rawalpindi"
    assert result["rain_probability_percent"] == 5.0
