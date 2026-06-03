"""The Reason payload: structured, controlled-vocabulary explanations for the
decisions an agent took on a turn.

Reasons are subject-relation-object triples drawn from closed vocabularies, not
free-text rationalisation. Both ``claim`` and ``relation`` are fixed sets; new
members are a deliberate, breaking vocabulary change, never an ad-hoc string.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Claim = Literal["included", "excluded", "added", "matched", "substituted", "note"]

Relation = Literal[
    "loads_joint",
    "matches_target",
    "bilateral_pair_of",
    "equipment_match",
    "name_match",
]


class Reason(BaseModel):
    """One explanation triple for a decision the agent made this turn."""

    claim: Claim
    subject: str
    relation: Relation
    object: str | None = None
    detail: str | None = None
