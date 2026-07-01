# SkyWise —  Outdoor Activity Planner

> A production-quality **LangGraph Deep Agent** that answers weather-dependent
> outdoor activity questions using **live weather data** and an **open-source LLM**.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Tech Stack](#tech-stack)
- [Environment Variables](#environment-variables)
- [Running Locally (Dev)](#running-locally-dev)
- [Running with Docker](#running-with-docker)
- [API Reference](#api-reference)
- [Deployment](#deployment)
  - [Backend → Railway](#backend--railway)
  - [Frontend → Vercel](#frontend--vercel)
- [Testing](#testing)
- [Future Improvements](#future-improvements)
- [Screenshots](#screenshots)

---

## Project Overview

**SkyWise** is a conversational AI agent that helps users make informed outdoor
decisions by combining live weather intelligence with deep domain knowledge
about sports, driving conditions, clothing, health, and more.

Example questions it handles brilliantly:

| Question | What it does |
|---|---|
| Can I play cricket tomorrow? | Checks rain probability, wind, humidity |
| Is it good for hiking today? | Evaluates visibility, temperature, wind on terrain |
| Should I carry an umbrella? | Runs rain-probability forecast |
| What should I wear today? | Derives clothing advice from heat index + humidity |
| Is it safe to drive tonight? | Assesses visibility, rain, wind for driving safety |
| Can I go cycling this evening? | Combines wind speed, precipitation, and daylight |

Unlike a plain chatbot, SkyWise **visibly uses tools** — the frontend shows
exactly which tools were called, with their inputs/outputs, execution time, and
agent reasoning.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Deep Agent                         │
│                                                                 │
│  START                                                          │
│    │                                                            │
│    ▼                                                            │
│  [intent_analysis]  — LLM extracts intent, city, activity       │
│    │                                                            │
│    ▼                                                            │
│  [decision]  ──────── conditional routing ─────────────────┐   │
│    │ needs_weather=True                  needs_weather=False│   │
│    ▼                                                        │   │
│  [weather_tool]  — calls OpenWeatherMap API                 │   │
│    │                                                        │   │
│    ▼                                                        │   │
│  [reasoning] ◄─────────────────────────────────────────────┘   │
│    │         — LLM reasons with weather data + domain knowledge │
│    ▼                                                            │
│  [response]  — finalise structured output, update message list  │
│    │                                                            │
│   END                                                           │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
FastAPI /api/chat
    │
    ▼
React Frontend (SkyWise Chat UI)
```

### Key Design Decisions

- **StateGraph** with typed `AgentState` (TypedDict) threads all data between
  nodes cleanly with Annotated reducers for append-only lists.
- **Conditional routing** via `route_after_decision` — the weather tool is only
  called when the user's intent actually requires live weather data, saving
  latency for purely conversational turns.
- **Checkpoint-ready** — uses `MemorySaver` locally, trivially swappable for
  `PostgresSaver` in production by changing one line in `graph.py`.
- **Open-source LLM** — wired through the `langchain-openai` client with a
  custom `base_url`, so it works with any OpenAI-compatible endpoint (Groq,
  Together AI, vLLM, Ollama with OpenAI compatibility layer).
- **Domain knowledge in prompts** — the reasoning system prompt encodes
  authoritative thresholds for rain, humidity, wind, temperature, visibility,
  and activity recommendations, so the LLM reasons rather than guesses.
- **Tool transparency** — every tool invocation is recorded with input, output,
  status, and duration, then surfaced in the API response and the UI.

---

## Folder Structure

```
weather-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI app + CORS + startup
│   │   ├── config.py      # Pydantic settings from .env
│   │   ├── schemas.py     # Request/response Pydantic models
│   │   ├── state.py       # Typed AgentState (TypedDict)
│   │   ├── prompts.py     # System prompts + domain knowledge
│   │   ├── tools.py       # Weather Tool (OpenWeatherMap)
│   │   ├── nodes.py       # LangGraph node functions
│   │   ├── graph.py       # StateGraph wiring + compilation
│   │   └── routes.py      # FastAPI route handlers
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_tools.py  # Weather tool unit tests
│   │   ├── test_nodes.py  # Node-level unit tests
│   │   └── test_api.py    # FastAPI integration tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── public/
│   │   └── icon.svg
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ChatMessage.jsx
│   │   │   ├── ChatInput.jsx
│   │   │   ├── TypingIndicator.jsx
│   │   │   ├── ThinkingPanel.jsx   # Tool calls + reasoning
│   │   │   ├── WeatherCard.jsx     # Live weather data card
│   │   │   ├── SuggestionPills.jsx
│   │   │   └── ErrorBanner.jsx
│   │   ├── api.js          # Axios API client
│   │   ├── App.jsx         # Root component + chat orchestration
│   │   ├── main.jsx        # React entry point
│   │   └── index.css       # Tailwind + custom utilities
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.115 + Uvicorn |
| Agent framework | LangGraph 0.2 + LangChain 0.3 |
| LLM client | langchain-openai (OpenAI-compatible endpoint) |
| LLM provider | Groq (llama-3.3-70b-versatile) or any OpenAI-compatible |
| Weather API | OpenWeatherMap (free tier) |
| Data validation | Pydantic v2 + pydantic-settings |
| Frontend | React 18 + Vite 6 + TailwindCSS 3 |
| HTTP client | Axios |
| Icons | lucide-react |
| Containerisation | Docker + Docker Compose |

---

