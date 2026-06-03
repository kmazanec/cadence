"""The single model-construction seam.

Every agent node obtains its model through :func:`get_model`; no node builds a
client directly. Tests override this one function to inject a deterministic,
network-free stub.
"""

from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .config import API_KEY_ENV, MODEL_CONFIG, OPENROUTER_BASE_URL, Role


def get_model(role: Role) -> BaseChatModel:
    """Return the chat model configured for a role, via OpenRouter."""

    model_id = MODEL_CONFIG[role]
    api_key = os.environ.get(API_KEY_ENV)
    return ChatOpenAI(
        model=model_id,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(api_key) if api_key is not None else None,
    )
