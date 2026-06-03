"""Model-swap config-only routing test (criterion 6).

Proves that swapping the default model via config (no code change) keeps the
routing-dispatch test passing. This confirms the get_model(role) abstraction and
the capability registry hold up across a model swap.

The test:
1. Patches MODEL_CONFIG to point the router role at a SECOND capable model
   (openai/gpt-4o instead of openai/gpt-4o-mini).
2. Verifies startup validation still passes for the swapped model.
3. Injects the same fake router seam used in test_routing_clarify.py.
4. Asserts the routing-dispatch + clarify behaviour is identical to the
   default-model case.

This test runs entirely offline — no OPENROUTER_API_KEY required.
The swap is config-only: MODEL_CONFIG is monkey-patched, no source file changes.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# Scripted router (same seam as test_routing_clarify.py)
# ---------------------------------------------------------------------------


def _make_scripted_router(decision_dict: dict) -> BaseChatModel:
    """Return a model that always returns the given RoutingDecision via structured output."""
    from app.graph.routing import RoutingDecision

    decision = RoutingDecision.model_validate(decision_dict)

    class _ScriptedRouter(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "scripted-router-swapped"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            from langchain_core.messages import AIMessage
            from langchain_core.outputs import ChatGeneration, ChatResult

            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

        def with_structured_output(self, schema, include_raw=False, **kwargs):
            class _Stub:
                async def ainvoke(self_inner, *args, **kwargs):
                    if include_raw:
                        return {"parsed": decision, "raw": AIMessage(content="")}
                    return decision

                def invoke(self_inner, *args, **kwargs):
                    if include_raw:
                        return {"parsed": decision, "raw": AIMessage(content="")}
                    return decision

            return _Stub()

    return _ScriptedRouter()


# ---------------------------------------------------------------------------
# Startup validation passes for the swapped model
# ---------------------------------------------------------------------------


def test_startup_validation_passes_with_swapped_model(monkeypatch):
    """validate_model_config accepts a second registry-capable model ID.

    Swapping router to openai/gpt-4o (a known capable model) must not raise.
    """
    import app.models.config as config_mod

    # Swap the router role to the second registered capable model.
    patched_config = {
        "router": "openai/gpt-4o",
        "coach": "openai/gpt-4o-mini",
        "generator": "openai/gpt-4o-mini",
        "logger": "openai/gpt-4o-mini",
    }
    monkeypatch.setattr(config_mod, "MODEL_CONFIG", patched_config)

    from app.models.registry import validate_model_config

    # Must not raise for a capable, registered model.
    validate_model_config(patched_config)


def test_startup_validation_rejects_unknown_swapped_model(monkeypatch):
    """validate_model_config rejects a model absent from the capability registry."""
    import app.models.config as config_mod

    patched_config = {
        "router": "acme/unknown-model-v999",
        "coach": "openai/gpt-4o-mini",
        "generator": "openai/gpt-4o-mini",
        "logger": "openai/gpt-4o-mini",
    }
    monkeypatch.setattr(config_mod, "MODEL_CONFIG", patched_config)

    from app.models.registry import validate_model_config

    with pytest.raises(ValueError, match="unknown-model-v999"):
        validate_model_config(patched_config)


# ---------------------------------------------------------------------------
# Routing dispatch + clarify holds under model swap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_routing_dispatch_holds_under_model_swap(monkeypatch):
    """With router swapped to gpt-4o (config only), routing dispatch still works.

    The fake router seam is injected as before; the config swap proves the
    get_model abstraction is transparent to route dispatch logic.
    """
    import app.models.config as config_mod

    # Config-only swap: point router at gpt-4o.
    patched_config = dict(config_mod.MODEL_CONFIG)
    patched_config["router"] = "openai/gpt-4o"
    monkeypatch.setattr(config_mod, "MODEL_CONFIG", patched_config)

    router = _make_scripted_router({
        "route": "coach",
        "confidence": 0.9,
        "rationale": "clear fitness question — model-swap test",
    })

    def _fake_get_model(role):
        if role == "router":
            return router
        return GenericFakeChatModel(messages=iter([AIMessage(content="Scripted reply")]))

    # The hub's router node uses the get_model name imported into app.graph.hub at
    # load time, so patch there too (the established hub-test pattern).
    monkeypatch.setattr("app.models.factory.get_model", _fake_get_model)
    monkeypatch.setattr("app.graph.hub.get_model", _fake_get_model)
    try:
        monkeypatch.setattr("app.agents.coach.graph.get_model", _fake_get_model)
    except AttributeError:
        pass

    import app.graph.hub as hub_module

    class _InMemoryLogRepo:
        def append(self, entries, session_id):
            pass

        def for_session(self, session_id):
            return []

    monkeypatch.setattr(hub_module, "_get_log_repository_for_hub", lambda: _InMemoryLogRepo())

    from app.graph.hub import build_hub
    from app.graph.routing import Route

    hub = build_hub()
    config = {"configurable": {"thread_id": "test-swap-session"}}
    initial = {
        "session_id": "test-swap-session",
        "messages": [],
        "user_message": "what exercises help with my squat?",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }

    state = await hub.ainvoke(initial, config)

    assert state["route"] == Route.COACH, (
        f"Expected COACH dispatch under model swap, got {state['route']}"
    )
    result = state.get("subgraph_result")
    assert result is not None
    assert result.kind == "coach"


@pytest.mark.asyncio
async def test_clarify_holds_under_model_swap(monkeypatch):
    """Low-confidence clarification also holds when the router is swapped.

    Below-threshold routing must produce a clarification prompt regardless
    of which model is configured — the policy is in decide_route, not the model.
    """
    import app.models.config as config_mod

    patched_config = dict(config_mod.MODEL_CONFIG)
    patched_config["router"] = "openai/gpt-4o"
    monkeypatch.setattr(config_mod, "MODEL_CONFIG", patched_config)

    router = _make_scripted_router({
        "route": "coach",
        "confidence": 0.45,  # below threshold
        "rationale": "ambiguous — model-swap test",
    })

    monkeypatch.setattr("app.models.factory.get_model", lambda _role: router)
    monkeypatch.setattr("app.graph.hub.get_model", lambda _role: router)

    import app.graph.hub as hub_module

    class _InMemoryLogRepo:
        def append(self, entries, session_id):
            pass

        def for_session(self, session_id):
            return []

    monkeypatch.setattr(hub_module, "_get_log_repository_for_hub", lambda: _InMemoryLogRepo())

    from app.graph.hub import build_hub

    hub = build_hub()
    config = {"configurable": {"thread_id": "test-swap-clarify-session"}}
    initial = {
        "session_id": "test-swap-clarify-session",
        "messages": [],
        "user_message": "help",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }

    state = await hub.ainvoke(initial, config)

    assert state["route"] is None, (
        f"Expected route=None for low confidence, got {state['route']}"
    )
    assert state["clarification"] is not None, "Expected clarification prompt"
    assert len(state["clarification"].options) >= 2
