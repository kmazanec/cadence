"""Logger subgraph: extract structured log entries from a free-text message,
resolve exercise names against the catalogue, and persist the results.

A single LLM call parses the user's message into zero or more
``ParsedEntry`` objects (name + sets/reps/weight). Each parsed entry is
then resolved through the fuzzy-match resolver. Entries that cannot be
matched are flagged ``unmatched`` and included as-is — never invented.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import app.models.factory as _factory
from pydantic import BaseModel

from app.data.json_repository import JsonExerciseRepository
from app.data.log_repository import LogEntry, LogRepository, get_log_repository
from app.data.repository import ExerciseRepository
from app.graph.state import WorkoutLogResult

from .resolver import resolve_exercise_name
from .state import LoggerState

# ---------------------------------------------------------------------------
# Parsed intermediate (LLM structured output)
# ---------------------------------------------------------------------------


class ParsedEntry(BaseModel):
    """One exercise mention extracted from the user's free-text message."""

    raw_name: str
    sets: int | None = None
    reps: int | None = None
    weight: float | None = None


class ParsedEntries(BaseModel):
    """All exercise mentions extracted from the message."""

    entries: list[ParsedEntry] = []


# ---------------------------------------------------------------------------
# LLM extraction (test-seam: monkeypatched in tests)
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = (
    "You are an exercise log parser. "
    "Extract every exercise the user mentions from their message. "
    "For each exercise, extract: the exercise name (as the user said it), "
    "the number of sets, the number of reps per set, and the weight (in lbs or kg, "
    "as a float — omit the unit). "
    "If any field is not mentioned, leave it null. "
    "Return a JSON object with an 'entries' list."
)


async def _extract_entries(user_message: str, model: Any) -> list[ParsedEntry]:
    """Use the model to extract parsed entries from the user's message."""
    from langchain_core.messages import HumanMessage, SystemMessage

    structured = model.with_structured_output(ParsedEntries)
    result: ParsedEntries = await structured.ainvoke(
        [
            SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
    )
    return result.entries


# ---------------------------------------------------------------------------
# Core logger logic
# ---------------------------------------------------------------------------


async def run_logger(
    user_message: str,
    session_id: str,
    repo: ExerciseRepository | None = None,
    log_repo: LogRepository | None = None,
    *,
    llm_verify: bool = True,
) -> WorkoutLogResult:
    """Parse, resolve, and persist workout log entries from a user message.

    Accepts optional repository overrides for testing; uses the production
    repositories by default.
    """
    if repo is None:
        repo = JsonExerciseRepository()
    if log_repo is None:
        log_repo = get_log_repository()

    model = _factory.get_model("logger")
    parsed = await _extract_entries(user_message, model)

    now = datetime.now(timezone.utc)
    entries: list[LogEntry] = []
    for p in parsed:
        match = resolve_exercise_name(p.raw_name, repo, llm_verify=llm_verify)
        if match is not None:
            exercise_id, _exercise_name = match
            entry = LogEntry(
                session_id=session_id,
                exercise_id=exercise_id,
                raw_name=p.raw_name,
                sets=p.sets,
                reps=p.reps,
                weight=p.weight,
                unmatched=False,
                logged_at=now,
            )
        else:
            entry = LogEntry(
                session_id=session_id,
                exercise_id=None,
                raw_name=p.raw_name,
                sets=p.sets,
                reps=p.reps,
                weight=p.weight,
                unmatched=True,
                logged_at=now,
            )
        entries.append(entry)

    if entries:
        log_repo.append(entries, session_id)

    return WorkoutLogResult(entries=entries, session_id=session_id)
