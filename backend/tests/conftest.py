"""Shared test fixtures.

The fake-model fixture overrides the single model-construction seam so tests run
deterministically with no network. The stub emits multi-chunk token deltas and
supports the structured-output and tool-binding surfaces agents rely on.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.models.config import Role


def make_fake_model(text: str = "Hello there, friend") -> BaseChatModel:
    """Return a deterministic, network-free chat model that streams in chunks.

    ``GenericFakeChatModel`` splits a returned message across multiple stream
    chunks on whitespace, exercising multi-delta token handling.
    """

    return GenericFakeChatModel(messages=iter([AIMessage(content=text)]))


@pytest.fixture
def fake_get_model(monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch ``get_model`` to return the deterministic stub.

    Returns the installer so a test can choose the canned response text.
    """

    def install(text: str = "Hello there, friend") -> None:
        def _fake(role: Role) -> BaseChatModel:
            return make_fake_model(text)

        monkeypatch.setattr("app.models.factory.get_model", _fake)

    install()
    return install
