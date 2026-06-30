"""
FastAPI application entrypoint for the Weather & Outdoor Activity Planner
Deep Agent backend.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import configure_logging, get_settings
from app.routes import router

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SkyWise Weather Agent backend in '%s' environment.", settings.app_env)
    yield
    logger.info("Shutting down SkyWise Weather Agent backend.")


app = FastAPI(
    title="SkyWise — Weather & Outdoor Activity Planner Agent",
    description=(
        "A LangGraph-powered Deep Agent that answers weather-dependent "
        "outdoor activity questions using live weather data and an "
        "open-source LLM."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "message": "SkyWise Weather Agent API. See /docs for interactive documentation."
    }
