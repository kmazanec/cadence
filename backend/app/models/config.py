"""Role-to-model mapping and the env keys the model layer reads.

One capable default backs every role; any role can be pointed at a different
model id without code changes.
"""

from __future__ import annotations

from typing import Literal

Role = Literal["router", "coach", "generator", "logger"]

# Roles whose model must support structured output / tool calling. The logger is
# included because name resolution verifies its fuzzy-match shortlist with the
# model.
STRUCTURED_OUTPUT_ROLES: tuple[Role, ...] = ("router", "generator", "logger")

# OpenRouter's OpenAI-compatible endpoint and the env key holding the API key.
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
API_KEY_ENV: str = "OPENROUTER_API_KEY"

# One shared capable default; override per role as needed.
DEFAULT_MODEL_ID: str = "openai/gpt-4o-mini"

MODEL_CONFIG: dict[Role, str] = {
    "router": DEFAULT_MODEL_ID,
    "coach": DEFAULT_MODEL_ID,
    "generator": DEFAULT_MODEL_ID,
    "logger": DEFAULT_MODEL_ID,
}
