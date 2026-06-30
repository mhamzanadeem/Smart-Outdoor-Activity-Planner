# SkyWise — AI Weather & Outdoor Activity Planner

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

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `WEATHER_API_KEY` | ✅ | — | OpenWeatherMap API key |
| `WEATHER_API_BASE_URL` | ❌ | `https://api.openweathermap.org/data/2.5` | Weather API base URL |
| `LLM_API_KEY` | ✅ | — | API key for LLM provider (e.g. Groq) |
| `LLM_API_BASE_URL` | ✅ | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL_NAME` | ❌ | `llama-3.3-70b-versatile` | Model identifier |
| `LLM_TEMPERATURE` | ❌ | `0.3` | Sampling temperature |
| `APP_ENV` | ❌ | `development` | Environment label |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |
| `CORS_ORIGINS` | ❌ | `http://localhost:5173` | Comma-separated allowed origins |
| `REQUEST_TIMEOUT_SECONDS` | ❌ | `20` | Timeout for external API calls |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | ❌ | `/api` | Backend API URL (for production set Railway URL) |

---

## Running Locally (Dev)

### Prerequisites

- Python 3.12+
- Node.js 20+
- OpenWeatherMap API key (free at https://openweathermap.org/api)
- Groq API key (free at https://console.groq.com) _or_ any OpenAI-compatible LLM endpoint

### 1. Backend

```bash
cd backend

# Copy and fill in your API keys
cp .env.example .env
# Edit .env with your WEATHER_API_KEY and LLM_API_KEY

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (proxies /api → localhost:8000 automatically)
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Running with Docker

```bash
# 1. Populate backend environment variables
cp backend/.env.example backend/.env
# Edit backend/.env

# 2. Build and start both services
docker compose up --build

# App will be available at http://localhost:80
# API at http://localhost:8000
```

To run in detached mode:

```bash
docker compose up --build -d
docker compose logs -f
```

To stop:

```bash
docker compose down
```

---

## API Reference

### `GET /api/health`

Returns service health.

```json
{ "status": "ok", "app_env": "development" }
```

### `POST /api/chat`

Main chat endpoint.

**Request body:**

```json
{
  "message": "Can I play cricket tomorrow in Lahore?",
  "session_id": "optional-uuid-for-conversation-memory"
}
```

**Response:**

```json
{
  "session_id": "abc123",
  "user_query": "Can I play cricket tomorrow in Lahore?",
  "final_answer": "Yes, tomorrow looks excellent for cricket in Lahore! ...",
  "reasoning": "Wind speed is only 8 km/h and rain probability is 5%, well below the 20% threshold ...",
  "tool_called": true,
  "intent": "sports_feasibility",
  "city": "Lahore",
  "tool_executions": [
    {
      "tool_name": "get_weather",
      "input": { "city": "Lahore" },
      "output": {
        "city": "Lahore",
        "temperature_c": 34.2,
        "feels_like_c": 36.1,
        "humidity_percent": 45,
        "wind_speed_kmh": 8.0,
        "visibility_km": 10.0,
        "condition": "Clear",
        "description": "clear sky",
        "rain_probability_percent": 5.0,
        "is_daytime": true
      },
      "status": "success",
      "duration_ms": 213.4
    }
  ],
  "weather_data": { "...": "same as tool output" }
}
```

---

## Deployment

### Backend → Railway

1. Create a new project on [Railway](https://railway.app).
2. Connect your GitHub repository and select the `backend/` directory.
3. Set the following environment variables in the Railway dashboard:

```
WEATHER_API_KEY=...
LLM_API_KEY=...
LLM_API_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_NAME=llama-3.3-70b-versatile
APP_ENV=production
CORS_ORIGINS=https://your-frontend.vercel.app
LOG_LEVEL=INFO
```

4. Railway will auto-detect the `Dockerfile` and deploy. Note your service URL
   (e.g. `https://skywise-backend.up.railway.app`).

### Frontend → Vercel

1. Push the repository to GitHub.
2. Import the project on [Vercel](https://vercel.com), set **Root Directory** to `frontend/`.
3. Set the following environment variable:

```
VITE_API_BASE_URL=https://skywise-backend.up.railway.app/api
```

4. Deploy. Vercel will run `npm run build` automatically.

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

Tests cover:

- **`test_tools.py`** — weather data fetching, unit conversions, error handling, LangChain tool invocation
- **`test_nodes.py`** — all five graph nodes individually, conditional routing logic, JSON parsing fallbacks
- **`test_api.py`** — FastAPI endpoint contracts, validation, session handling, error propagation

---

## Future Improvements

- [ ] **Streaming responses** — stream the LLM's token output via SSE / WebSocket for perceived speed
- [ ] **Persistent checkpointing** — swap `MemorySaver` for `PostgresSaver` to persist conversation history across restarts
- [ ] **Multi-day forecasts** — extend the weather tool to return 5-day hourly forecasts
- [ ] **Pollen / UV index** — integrate additional APIs for health-sensitive recommendations
- [ ] **Geolocation** — auto-detect user city from browser geolocation API
- [ ] **Push notifications** — alert users when weather crosses a user-set threshold
- [ ] **LangSmith tracing** — plug in LangSmith for full observability of graph executions
- [ ] **Authentication** — add user accounts so conversation history is persistent per user
- [ ] **Mobile app** — React Native or Progressive Web App (PWA) wrapper

---

## Screenshots

_Coming soon — replace with actual screenshots after deployment._

| Welcome Screen | Active Conversation | Tool Execution Panel |
|---|---|---|
| ![Welcome](docs/screenshots/welcome.png) | ![Chat](docs/screenshots/chat.png) | ![Tools](docs/screenshots/tools.png) |

---

## License

MIT
