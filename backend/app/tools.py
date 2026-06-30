"""
Weather Tool: fetches live weather data for a given city.

Uses the OpenWeatherMap "current weather" + "forecast" endpoints to derive
temperature, humidity, wind speed, visibility, condition, and a rain
probability estimate. Implemented as a LangChain @tool so the agent graph
can invoke it explicitly.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger(__name__)


class WeatherToolInput(BaseModel):
    city: str = Field(..., description="The city name to fetch weather for, e.g. 'Rawalpindi'")


class WeatherToolError(Exception):
    """Raised when the weather provider cannot return usable data."""


def _kmh_from_ms(speed_ms: float) -> float:
    return round(speed_ms * 3.6, 1)


def _fetch_current_weather(city: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.weather_api_key:
        raise WeatherToolError(
            "WEATHER_API_KEY is not configured. Set it in your .env file."
        )

    url = f"{settings.weather_api_base_url}/weather"
    params = {
        "q": city,
        "appid": settings.weather_api_key,
        "units": "metric",
    }
    response = requests.get(url, params=params, timeout=settings.request_timeout_seconds)
    if response.status_code == 404:
        raise WeatherToolError(f"City '{city}' was not found by the weather provider.")
    response.raise_for_status()
    return response.json()


def _fetch_rain_probability(city: str) -> float:
    """Estimate rain probability using the next forecast slot (3-hour step)."""
    settings = get_settings()
    try:
        url = f"{settings.weather_api_base_url}/forecast"
        params = {
            "q": city,
            "appid": settings.weather_api_key,
            "units": "metric",
            "cnt": 4,
        }
        response = requests.get(url, params=params, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        slots = data.get("list", [])
        if not slots:
            return 0.0
        probs = [slot.get("pop", 0.0) for slot in slots]
        return round((sum(probs) / len(probs)) * 100, 1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rain probability forecast lookup failed for %s: %s", city, exc)
        return 0.0


def fetch_weather_data(city: str) -> dict[str, Any]:
    """
    Core synchronous implementation used both by the LangChain tool wrapper
    and directly by graph nodes/tests.
    """
    start = time.perf_counter()
    raw = _fetch_current_weather(city)

    main = raw.get("main", {})
    wind = raw.get("wind", {})
    weather_list = raw.get("weather", [{}])
    weather_info = weather_list[0] if weather_list else {}
    sys_info = raw.get("sys", {})
    visibility_m = raw.get("visibility", 10000)

    rain_probability = _fetch_rain_probability(city)

    now = raw.get("dt", 0)
    sunrise = sys_info.get("sunrise", 0)
    sunset = sys_info.get("sunset", 1)
    is_daytime = sunrise <= now <= sunset if (sunrise and sunset) else True

    result = {
        "city": raw.get("name", city),
        "temperature_c": main.get("temp", 0.0),
        "feels_like_c": main.get("feels_like", main.get("temp", 0.0)),
        "humidity_percent": main.get("humidity", 0.0),
        "wind_speed_kmh": _kmh_from_ms(wind.get("speed", 0.0)),
        "visibility_km": round(visibility_m / 1000, 1),
        "condition": weather_info.get("main", "Unknown"),
        "description": weather_info.get("description", "unknown conditions"),
        "rain_probability_percent": rain_probability,
        "is_daytime": is_daytime,
    }
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info("Weather fetched for %s in %.1fms: %s", city, duration_ms, result)
    return result


@tool("get_weather", args_schema=WeatherToolInput)
def get_weather_tool(city: str) -> dict[str, Any]:
    """Fetch current weather conditions (temperature, humidity, wind speed,
    visibility, condition, and rain probability) for the given city. Use
    this whenever the user's question depends on real-world weather
    conditions, such as outdoor activities, clothing, or driving safety."""
    return fetch_weather_data(city)
