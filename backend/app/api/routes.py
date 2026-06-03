"""HTTP surface for the chat endpoint.

The serializer is the single place that turns committed hub state into the wire
envelope; it delegates the producer-arm switch to the response-assembly node so
the two stay in lockstep. Driving the graph and streaming live tokens is wired
on top of this shape.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..graph.response_assembly import assemble_response
from ..graph.state import HubState
from .schemas import ChatResponse

router = APIRouter()


def serialize_response(state: HubState) -> ChatResponse:
    """Serialise committed hub state into the outbound chat envelope."""

    return assemble_response(state)
