"""
Pydantic request/response schemas for the public API.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's chat message")
    session_id: str | None = Field(default=None, description="Optional conversation/session identifier")


class WeatherData(BaseModel):
    city: str
    temperature_c: float
    feels_like_c: float
    humidity_percent: float
    wind_speed_kmh: float
    visibility_km: float
    condition: str
    description: str
    rain_probability_percent: float
    is_daytime: bool


class ToolExecution(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    status: Literal["success", "error", "skipped"]
    duration_ms: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    user_query: str
    final_answer: str
    reasoning: str
    tool_called: bool
    tool_executions: list[ToolExecution] = Field(default_factory=list)
    weather_data: WeatherData | None = None
    intent: str | None = None
    city: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app_env: str
