"""The /chat SSE endpoint: drives the hub graph and streams events to the client.

Token events originate from model-message deltas, filtered to the node
producing the reply. Route, structured, and clarification events are read from
committed graph state, never from message deltas — this is the safe pattern
from ADR-002 that avoids tool-argument corruption.
"""

from __future__ import annotations

import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk

from ..api.streaming import (
    ClarificationEvent,
    DoneEvent,
    ErrorEvent,
    RouteEvent,
    TokenEvent,
    encode_sse,
)
from ..graph.hub import build_hub
from ..graph.state import HubState
from .schemas import ChatRequest

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
    """
    session_id = request.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

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

        async for _ns, mode, data in _hub.astream(
            initial, config, stream_mode=["messages", "updates"], subgraphs=True
        ):
            if mode == "messages":
                msg, _meta = data
                # Emit token events for AI message chunks with content.
                if isinstance(msg, AIMessageChunk) and msg.content:
                    yield encode_sse(TokenEvent(text=str(msg.content)))

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
