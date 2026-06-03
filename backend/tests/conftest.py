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

    Set ``simulate_null_parse=True`` to simulate a structured-output parse
    failure (the router node will receive ``parsed=None`` in the include_raw
    result dict).

    Streaming delegates to GenericFakeChatModel so token-delta tests pass.
    """

    parsed_result: RoutingDecision | None = None  # type: ignore[assignment]
    simulate_null_parse: bool = False
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
        # The single fake-model seam serves every structured-output role. When a
        # non-router schema is requested (e.g. the logger's ParsedEntries), return
        # an empty/default instance of that schema rather than a RoutingDecision —
        # otherwise wiring the logger into the hub makes router-focused dispatch
        # tests fail on a schema mismatch. Router tests that need a specific
        # decision still pass it via parsed_result.
        if schema is not RoutingDecision and isinstance(schema, type):
            try:
                instance = schema()
            except Exception:
                instance = None
            if include_raw:
                return RunnableLambda(
                    lambda _: {
                        "raw": AIMessage(content=self.chat_text),
                        "parsed": instance,
                        "parsing_error": None,
                    }
                )
            return RunnableLambda(lambda _: instance)

        # simulate_null_parse=True → emit parsed=None to exercise the safe-net path.
        # parsed_result=None (default) → fall back to a default high-confidence COACH
        # decision so hub integration tests reach the coach subgraph without setup.
        if self.simulate_null_parse:
            decision: RoutingDecision | None = None
        elif self.parsed_result is None:
            decision = RoutingDecision(
                route=Route.COACH,
                confidence=0.9,
                rationale="fake router — always coach",
            )
        else:
            decision = self.parsed_result

        raw_msg = AIMessage(content=self.chat_text)

        if include_raw:
            result = {
                "raw": raw_msg,
                "parsed": decision,
                "parsing_error": None if decision is not None else Exception("parse failed"),
            }
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
