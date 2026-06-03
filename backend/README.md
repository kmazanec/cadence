# Cadence backend

FastAPI + LangGraph backend for the Cadence fitness chat coach.

## Setup

```bash
uv sync
cp .env.example .env   # then fill in OPENROUTER_API_KEY
uv run pytest
```

## Models (role → model map)

Every agent role obtains its model through the single `get_model(role)` factory
(`app/models/factory.py`); no node constructs a client directly. The role →
model mapping lives in `app/models/config.py` and is overridable per role:

| Role        | Default model        | Structured output required |
| ----------- | -------------------- | -------------------------- |
| `router`    | `openai/gpt-4o-mini` | yes                        |
| `coach`     | `openai/gpt-4o-mini` | no                         |
| `generator` | `openai/gpt-4o-mini` | yes                        |
| `logger`    | `openai/gpt-4o-mini` | yes (name-match verify)    |

`validate_model_config()` runs at startup and fails fast if any
structured-output role maps to a model that is unknown to the capability
registry (`app/models/registry.py`) or lacks structured-output support. To
split-test a role, point its entry in `config.py` at another registered model
id — no code change required.
