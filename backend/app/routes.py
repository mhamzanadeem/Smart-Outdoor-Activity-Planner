"""
API route definitions.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from app.graph import agent_graph
from app.schemas import ChatRequest, ChatResponse, HealthResponse, ToolExecution, WeatherData
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app_env=settings.app_env)


@router.post("/chat", response_model=ChatResponse, tags=["agent"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main conversational endpoint. Runs the LangGraph Deep Agent and returns
    a structured response including reasoning and tool execution details.
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info("Received chat request session=%s message=%r", session_id, request.message)

    # Fast-fail config check: return a clear error before hitting the LLM
    settings = get_settings()
    if not settings.llm_api_key:
        return ChatResponse(
            session_id=session_id,
            user_query=request.message,
            final_answer="",
            reasoning="",
            tool_called=False,
            error_code="llm_api_key_missing",
            error_message=(
                "⚠️ LLM API key is not configured. "
                "Please set `LLM_API_KEY` in your `backend/.env` file and restart the server."
            ),
        )

    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "user_query": request.message,
        "session_id": session_id,
    }
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await agent_graph.ainvoke(initial_state, config=config)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent graph execution failed: %s", exc)
        raise HTTPException(status_code=500, detail="Agent failed to process the request.") from exc

    weather_payload = result.get("weather_data")
    weather_data = WeatherData(**weather_payload) if weather_payload else None

    tool_executions = [
        ToolExecution(
            tool_name=record.get("tool_name", "get_weather"),
            input=record.get("input", {}),
            output=record.get("output"),
            status=record.get("status", "skipped"),
            duration_ms=record.get("duration_ms"),
        )
        for record in result.get("tool_executions", [])
    ]

    # Pick up error info propagated through the agent state
    error_code = result.get("error_code")
    error_message = result.get("error") if error_code else None

    return ChatResponse(
        session_id=session_id,
        user_query=request.message,
        final_answer=result.get("final_answer", ""),
        reasoning=result.get("reasoning", ""),
        tool_called=result.get("tool_called", False),
        tool_executions=tool_executions,
        weather_data=weather_data,
        intent=result.get("intent"),
        city=result.get("city"),
        error_code=error_code,
        error_message=error_message,
    )
