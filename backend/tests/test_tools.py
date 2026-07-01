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

    result = tools.fetch_weather_data("Rawalpindi", timeframe="current")

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
        tools.fetch_weather_data("NotARealCity12345", timeframe="current")


def test_get_weather_tool_invocation(monkeypatch, mock_current_weather_response):
    monkeypatch.setattr(tools, "_fetch_current_weather", lambda city: mock_current_weather_response)
    monkeypatch.setattr(tools, "_fetch_rain_probability", lambda city: 5.0)

    result = tools.get_weather_tool.invoke({"city": "Rawalpindi", "timeframe": "current"})
    assert result["city"] == "Rawalpindi"
    assert result["rain_probability_percent"] == 5.0


def test_fetch_weather_data_future_uses_open_meteo(monkeypatch):
    monkeypatch.setattr(tools, "_fetch_open_meteo_coordinates", lambda city: (33.6, 73.0, "Rawalpindi"))
    monkeypatch.setattr(
        tools,
        "_fetch_open_meteo_daily_forecast",
        lambda lat, lon: {
            "daily": {
                "time": ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"],
                "weather_code": [2, 0, 80, 82],
                "temperature_2m_max": [35.6, 39.5, 41.1, 37.7],
                "temperature_2m_min": [23.8, 26.8, 26.2, 24.1],
            }
        },
    )

    result = tools.fetch_weather_data("Rawalpindi", timeframe="tomorrow")

    assert result["city"] == "Rawalpindi"
    assert result["forecast_date"] == "2026-07-02"
    assert result["weather_code"] == 0
    assert result["temperature_c"] == 39.5
    assert result["night_min_c"] == 26.8
    assert result["condition"] == "Clear sky"


def test_open_meteo_description_mapping():
    assert tools._open_meteo_description(0) == "Clear sky"
    assert tools._open_meteo_description(82) == "Rain showers (violent)"
    assert tools._open_meteo_description(999) == "Unknown weather"
