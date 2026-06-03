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
from langchain_core.runnables import RunnableLambda

from app.graph.routing import Route, RoutingDecision
from app.models.config import Role


def make_fake_model(text: str = "Hello there, friend") -> BaseChatModel:
    """Return a deterministic, network-free chat model that streams in chunks.

    ``GenericFakeChatModel`` splits a returned message across multiple stream
    chunks on whitespace, exercising multi-delta token handling.
    """

    return GenericFakeChatModel(messages=iter([AIMessage(content=text)]))


class FakeStructuredOutputModel(BaseChatModel):
    """A network-free model for tests that need with_structured_output support.

    Returns the given ``parsed_result`` through the include_raw=True interface
    the router node uses. Falls back to a high-confidence COACH decision when
    no result is supplied, so hub integration tests reach the coach subgraph.

    Streaming delegates to GenericFakeChatModel so token-delta tests pass.
    """

    parsed_result: RoutingDecision | None = None
    chat_text: str = "Hello there, friend"

    @property
    def _llm_type(self) -> str:
        return "fake-structured-output"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.chat_text))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        """Stream the response in chunks via GenericFakeChatModel."""
        from langchain_core.messages import AIMessageChunk

        inner = GenericFakeChatModel(messages=iter([AIMessage(content=self.chat_text)]))
        async for chunk in inner._astream(messages, stop=stop):
            yield chunk

    def with_structured_output(self, schema, *, include_raw: bool = False, **kwargs):
        decision = self.parsed_result or RoutingDecision(
            route=Route.COACH,
            confidence=0.9,
            rationale="fake router — always coach",
        )
        raw_msg = AIMessage(content=self.chat_text)

        if include_raw:
            result = {"raw": raw_msg, "parsed": decision, "parsing_error": None}
        else:
            result = decision

        return RunnableLambda(lambda _: result)


@pytest.fixture
def fake_get_model(monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch ``get_model`` everywhere it is imported so tests run with no network.

    The router node calls get_model('router').with_structured_output(…), so the
    fake model returned must support that interface. All other roles fall back to
    a GenericFakeChatModel for token streaming.

    Returns an installer callable so a test can choose canned text or decision.
    """

    def install(
        text: str = "Hello there, friend",
        routing_decision: RoutingDecision | None = None,
    ) -> None:
        fake = FakeStructuredOutputModel(
            parsed_result=routing_decision,
            chat_text=text,
        )
        # Patch both the canonical location and any module that has already
        # imported the name at load time.
        monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)
        monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
        # Coach node patches via the coach graph module
        try:
            monkeypatch.setattr("app.agents.coach.graph.get_model", lambda role: fake)
        except AttributeError:
            pass

    install()
    return install
