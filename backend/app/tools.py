"""
Weather Tool: fetches live weather data for a given city.

Uses OpenWeatherMap for current weather and Open-Meteo daily forecast for
non-current requests (today/tomorrow/future day slots). Implemented as a
LangChain @tool so the agent graph can invoke it explicitly.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger(__name__)


class WeatherToolInput(BaseModel):
    city: str = Field(..., description="The city name to fetch weather for, e.g. 'Rawalpindi'")
    timeframe: str = Field(
        default="current",
        description="One of: current, today, tomorrow, 1 day after, 3 days after",
    )


class WeatherToolError(Exception):
    """Raised when the weather provider cannot return usable data."""


import urllib.parse

_OPEN_METEO_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle (light)",
    53: "Drizzle (moderate)",
    55: "Drizzle (dense)",
    56: "Freezing drizzle (light)",
    57: "Freezing drizzle (dense)",
    61: "Rain (slight)",
    63: "Rain (moderate)",
    65: "Rain (heavy)",
    66: "Freezing rain (light)",
    67: "Freezing rain (heavy)",
    71: "Snow fall (slight)",
    73: "Snow fall (moderate)",
    75: "Snow fall (heavy)",
    77: "Snow grains",
    80: "Rain showers (slight)",
    81: "Rain showers (moderate)",
    82: "Rain showers (violent)",
    85: "Snow showers (slight)",
    86: "Snow showers (heavy)",
    95: "Thunderstorm (slight or moderate)",
    96: "Thunderstorm with hail (slight)",
    99: "Thunderstorm with hail (heavy)",
}

def _kmh_from_ms(speed_ms: float) -> float:
    return round(speed_ms * 3.6, 1)


def _fetch_current_weather(city: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.weather_api_key:
        raise WeatherToolError(
            "WEATHER_API_KEY is not configured. Set it in your .env file."
        )

    encoded_city = urllib.parse.quote(city)
    # Using the exact URL template format requested
    url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded_city}&units=metric&appid={settings.weather_api_key}"
    response = requests.get(url, timeout=settings.request_timeout_seconds)
    if response.status_code == 404:
        raise WeatherToolError(f"City '{city}' was not found by the weather provider.")
    response.raise_for_status()
    return response.json()


def _fetch_rain_probability(city: str) -> float:
    """Estimate rain probability using the next forecast slot (3-hour step)."""
    settings = get_settings()
    try:
        encoded_city = urllib.parse.quote(city)
        # Using the exact forecast counterpart URL format
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={encoded_city}&units=metric&cnt=4&appid={settings.weather_api_key}"
        response = requests.get(url, timeout=settings.request_timeout_seconds)
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


def _open_meteo_description(code: int) -> str:
    return _OPEN_METEO_CODE_DESCRIPTIONS.get(code, "Unknown weather")


def _fetch_open_meteo_coordinates(city: str) -> tuple[float, float, str]:
    settings = get_settings()
    encoded_city = urllib.parse.quote(city)
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={encoded_city}&count=1&language=en&format=json"
    )
    response = requests.get(url, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    if not results:
        raise WeatherToolError(f"City '{city}' was not found by the weather provider.")
    first = results[0]
    return float(first["latitude"]), float(first["longitude"]), str(first.get("name", city))


def _fetch_open_meteo_daily_forecast(latitude: float, longitude: float) -> dict[str, Any]:
    settings = get_settings()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min"
        "&timezone=auto"
    )
    response = requests.get(url, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    return response.json()


def _build_weather_result_from_daily_slot(
    city: str,
    forecast_date: str,
    weather_code: int,
    day_max_c: float,
    night_min_c: float,
) -> dict[str, Any]:
    description = _open_meteo_description(weather_code)
    rainy_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    rain_probability = 70.0 if weather_code in rainy_codes else 10.0

    return {
        "city": city,
        "temperature_c": day_max_c,
        "feels_like_c": day_max_c,
        "humidity_percent": 0.0,
        "wind_speed_kmh": 0.0,
        "visibility_km": 0.0,
        "condition": description,
        "description": (
            f"Date: {forecast_date} | Code: {weather_code} | "
            f"Day Max: {day_max_c} C | Night Min: {night_min_c} C"
        ),
        "rain_probability_percent": rain_probability,
        "is_daytime": True,
        "weather_code": weather_code,
        "forecast_date": forecast_date,
        "day_max_c": day_max_c,
        "night_min_c": night_min_c,
        "timeframe_source": "open-meteo-daily",
    }


def _normalize_timeframe(timeframe: str | None) -> str:
    normalized = (timeframe or "current").strip().lower()
    valid = {"current", "today", "tomorrow", "1 day after", "3 days after"}
    return normalized if normalized in valid else "current"


def fetch_weather_data(city: str, timeframe: str = "current") -> dict[str, Any]:
    """
    Core synchronous implementation used both by the LangChain tool wrapper
    and directly by graph nodes/tests.
    """
    start = time.perf_counter()
    normalized_timeframe = _normalize_timeframe(timeframe)

    if normalized_timeframe != "current":
        latitude, longitude, resolved_city = _fetch_open_meteo_coordinates(city)
        forecast = _fetch_open_meteo_daily_forecast(latitude, longitude)
        daily = forecast.get("daily", {})
        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])

        offset_map = {
            "today": 0,
            "tomorrow": 1,
            "1 day after": 2,
            "3 days after": 3,
        }
        idx = offset_map[normalized_timeframe]

        if not (idx < len(dates) and idx < len(codes) and idx < len(max_temps) and idx < len(min_temps)):
            raise WeatherToolError(
                f"No forecast data available for '{city}' in timeframe '{normalized_timeframe}'."
            )

        result = _build_weather_result_from_daily_slot(
            city=resolved_city,
            forecast_date=str(dates[idx]),
            weather_code=int(codes[idx]),
            day_max_c=float(max_temps[idx]),
            night_min_c=float(min_temps[idx]),
        )

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "Open-Meteo forecast fetched for %s (%s) in %.1fms: %s",
            resolved_city,
            normalized_timeframe,
            duration_ms,
            result,
        )
        return result

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
def get_weather_tool(city: str, timeframe: str = "current") -> dict[str, Any]:
    """Fetch current weather conditions (temperature, humidity, wind speed,
    visibility, condition, and rain probability) for the given city. Use
    this whenever the user's question depends on real-world weather
    conditions, such as outdoor activities, clothing, or driving safety."""
    return fetch_weather_data(city, timeframe=timeframe)
