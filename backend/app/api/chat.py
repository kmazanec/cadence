"""The /chat SSE endpoint: drives the hub graph and streams events to the client.

Token events originate from model-message deltas, filtered to the node
producing the reply. Route, structured, and clarification events are read from
committed graph state, never from message deltas — this is the safe pattern
from ADR-002 that avoids tool-argument corruption.
"""

from __future__ import annotations

import logging
import uuid
from typing import AsyncIterator, cast

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import RunnableConfig

from ..api.streaming import (
    ClarificationEvent,
    DoneEvent,
    ErrorEvent,
    ExplanationEvent,
    RouteEvent,
    StructuredEvent,
    ThinkingEvent,
    TokenEvent,
    encode_sse,
)
from ..graph.hub import build_hub
from ..graph.response_assembly import assemble_response
from ..graph.state import HubState
from ..observability import logging as obs
from .schemas import ChatRequest

# The single node whose model output IS the user-facing reply. Every other node
# that runs a model (the router classifying, the generator's tool reasoning) has
# its deltas surfaced as deemphasized 'thinking', never as the reply. Naming the
# reply node explicitly is what keeps the router's structured-decision JSON out
# of the conversation (the bug where '{"route":...}' showed up as the answer).
_REPLY_NODE = "coach_answer"

logger = logging.getLogger(__name__)

router = APIRouter()

# One shared hub graph instance for the application lifetime.
# The MemorySaver checkpointer inside keeps sessions isolated by thread_id.
_hub = build_hub()


async def _stream_chat(request: ChatRequest) -> AsyncIterator[str]:
    """Drive the hub graph and yield SSE-encoded frames.

    Emits:
    - ``route`` once the router node commits a non-None route to state.
    - ``clarification`` when the run ends in the clarification branch (route is None).
    - ``token`` for each model message chunk (from the coach or future agents).
    - ``done`` when the graph run completes.
    - ``error`` if an unhandled exception escapes.

    Route and clarification events originate from committed graph state via the
    ``updates`` stream, never from message deltas — this is the ADR-002 safe
    pattern that prevents tool-argument text from leaking into events.

    The session_id is set on a ContextVar so every event emitted by downstream
    nodes during this request carries the correct correlation id without explicit
    threading.
    """
    session_id = request.session_id or str(uuid.uuid4())
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}

    # Bind the correlation id to the current async task; downstream emitters
    # read it from the ContextVar without needing it in their call signatures.
    sid_token = obs.session_id.set(session_id)

    initial: HubState = {
        "session_id": session_id,
        "messages": [],
        "user_message": request.message,
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }

    try:
        route_emitted = False
        clarification_emitted = False

        with obs.request_latency():
            async for _ns, mode, data in _hub.astream(
                initial, config, stream_mode=["messages", "updates"], subgraphs=True
            ):
                if mode == "messages":
                    msg, meta = data
                    if isinstance(msg, AIMessageChunk) and msg.content:
                        text = str(msg.content)
                        # The reply node's deltas are the answer; every other
                        # node's deltas (router classifying, generator reasoning)
                        # are 'thinking' — shown deemphasized, never as the reply.
                        node = meta.get("langgraph_node") if isinstance(meta, dict) else None
                        if node == _REPLY_NODE:
                            yield encode_sse(TokenEvent(text=text))
                        else:
                            # Tag the source so the client parses router fragments
                            # (partial decision JSON) differently from a subagent's
                            # prose, and never shows raw JSON.
                            yield encode_sse(
                                ThinkingEvent(source=str(node or "agent"), text=text)
                            )

                elif mode == "updates":
                    # updates data is {node_name: node_output_dict}.
                    # Route and clarification are read from committed state values,
                    # not reconstructed from message content.
                    if isinstance(data, dict):
                        for _node, node_out in data.items():
                            if not isinstance(node_out, dict):
                                continue

                            if not route_emitted:
                                route_val = node_out.get("route")
                                if route_val is not None:
                                    yield encode_sse(RouteEvent(route=route_val))
                                    route_emitted = True

                            if not clarification_emitted:
                                clarification_val = node_out.get("clarification")
                                if clarification_val is not None:
                                    yield encode_sse(
                                        ClarificationEvent(
                                            question=clarification_val.question,
                                            options=clarification_val.options,
                                        )
                                    )
                                    clarification_emitted = True

        # Emit the structured payload (a workout or a log) from committed state.
        # The generator and logger produce cards, not streamed prose — their
        # reply lives here, assembled from the final state via the same function
        # the non-streaming envelope uses, so the two stay in lock-step.
        snapshot = await _hub.aget_state(config)
        # snapshot.values is the committed HubState as a plain dict; cast to the
        # TypedDict so assemble_response sees the shape it expects.
        response = assemble_response(cast(HubState, snapshot.values))
        if response.structured is not None:
            yield encode_sse(StructuredEvent(payload=response.structured))

        # Emit the explanation payload on workout turns that produced reasons.
        # Coach and log turns produce no reasons, so the gate keeps them silent.
        if response.explanation:
            yield encode_sse(ExplanationEvent(reasons=response.explanation))

        yield encode_sse(DoneEvent())

    except Exception:  # noqa: BLE001
        # Log the full exception server-side for debugging, then emit a
        # sanitized error frame to the client — no traceback, no internal
        # detail. We deliberately do NOT re-raise: re-raising inside the
        # StreamingResponse generator makes Starlette discard the just-yielded
        # frame, so the client would receive an empty body instead of the
        # error event this boundary promises (ADR-006/014).
        logger.exception("Unhandled error in /chat stream")
        yield encode_sse(ErrorEvent(message="Something went wrong — please try again."))

    finally:
        # Restore the ContextVar to its previous state so the value does not
        # bleed into other async tasks sharing this event loop.
        obs.session_id.reset(sid_token)


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Accept a chat message and stream the reply as Server-Sent Events."""
    return StreamingResponse(
        _stream_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
