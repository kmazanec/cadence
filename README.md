# Cadence

Cadence is a multi-agent fitness coach that answers questions, generates
workouts, and logs sessions — delivered as a streaming chat interface.

## Quick start

**Prerequisites:** Docker and Docker Compose (or `uv` + Node 20 for local dev).

```bash
git clone <repo-url>
cd cadence
cp backend/.env.example backend/.env
# Add your OpenRouter API key to backend/.env
docker compose up
```

Open http://localhost:5173 in your browser.

## Local development (no Docker)

**Backend:**

```bash
cd backend
uv sync
cp .env.example .env   # fill in OPENROUTER_API_KEY
uv run uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/chat` to `http://localhost:8000`.

## Running tests

```bash
# Backend (uses the fake model — no API key required)
cd backend && uv run pytest

# Frontend
cd frontend && npm test
```

## Architecture

```
frontend (React + Vite + Tailwind)
    └── POST /chat  →  SSE stream
backend (FastAPI)
    └── /chat  →  hub StateGraph (LangGraph)
                     ├── router node  →  Route enum
                     ├── coach boundary  →  CoachState  →  CoachResult
                     ├── (generator boundary — future)
                     ├── (logger boundary — future)
                     └── response assembly  →  ChatResponse
```

### Model configuration

Every agent role resolves its model through `get_model(role)` in
`backend/app/models/factory.py`. The role-to-model map is in
`backend/app/models/config.py`; override any role by changing the model id
there — no code change required.

| Role        | Default                | Structured output |
|-------------|------------------------|-------------------|
| `router`    | `openai/gpt-4o-mini`   | required          |
| `coach`     | `openai/gpt-4o-mini`   | —                 |
| `generator` | `openai/gpt-4o-mini`   | required          |
| `logger`    | `openai/gpt-4o-mini`   | required          |

`validate_model_config()` runs at startup and refuses to start if a
structured-output role maps to an unknown or incapable model.

## Design tokens

All UI colors, fonts, and spacing come from `frontend/tailwind.config.js`.
The `accent` token (`#00C2A8`) is a teal-family default — see `frontend/BRAND.md`
for the eyedropper confirmation step against the live brand reference.
