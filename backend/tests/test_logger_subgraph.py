"""Tests for the logger subgraph end-to-end (deterministic, no live LLM).

The fake_get_model fixture stubs get_model so no network calls are made.
The subgraph is called directly via ainvoke with a pre-seeded extraction
result injected through a patched extraction helper, so LLM parsing is
bypassed and only the fuzzy-match + persistence path is exercised.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.agents.logger.graph import run_logger
from app.data.json_repository import JsonExerciseRepository
from app.data.log_repository import LogEntry
from app.data.sqlite_log_repository import SqliteLogRepository
from app.graph.state import WorkoutLogResult


@pytest.fixture
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


@pytest.fixture
def sqlite_repo(tmp_path):
    return SqliteLogRepository(tmp_path / "test.db")


@pytest.mark.asyncio
async def test_bench_press_resolves_and_persists(
    tmp_path, repo, fake_get_model, monkeypatch
) -> None:
    """'3x10 bench press at 185 lbs' → one entry resolved to a real exercise."""
    from app.agents.logger import graph as logger_graph
    from app.agents.logger.graph import ParsedEntry

    # Stub the extraction step so we don't need a real LLM.
    async def _fake_extract(user_message: str, model) -> list[ParsedEntry]:
        return [
            ParsedEntry(raw_name="bench press", sets=3, reps=10, weight=185.0)
        ]

    monkeypatch.setattr(logger_graph, "_extract_entries", _fake_extract)

    sqlite = SqliteLogRepository(tmp_path / "bench.db")
    result = await run_logger(
        user_message="I just did 3x10 bench press at 185 lbs",
        session_id="session-bench",
        repo=repo,
        log_repo=sqlite,
        llm_verify=False,
    )

    assert isinstance(result, WorkoutLogResult)
    assert result.session_id == "session-bench"
    assert len(result.entries) == 1

    entry = result.entries[0]
    assert entry.sets == 3
    assert entry.reps == 10
    assert entry.weight == 185.0
    assert entry.unmatched is False
    assert entry.exercise_id is not None
    assert "bench press" in entry.raw_name.lower()

    # Verify persistence.
    persisted = sqlite.for_session("session-bench")
    assert len(persisted) == 1
    assert persisted[0].exercise_id == entry.exercise_id


@pytest.mark.asyncio
async def test_unmatched_name_flagged_not_invented(
    tmp_path, repo, fake_get_model, monkeypatch
) -> None:
    """An unmatchable exercise is flagged unmatched, exercise_id is None."""
    from app.agents.logger import graph as logger_graph
    from app.agents.logger.graph import ParsedEntry

    async def _fake_extract(user_message: str, model) -> list[ParsedEntry]:
        return [
            ParsedEntry(raw_name="zercher good-mornings", sets=3, reps=10, weight=None)
        ]

    monkeypatch.setattr(logger_graph, "_extract_entries", _fake_extract)

    sqlite = SqliteLogRepository(tmp_path / "unmatched.db")
    result = await run_logger(
        user_message="I did 3x10 zercher good-mornings",
        session_id="session-unmatched",
        repo=repo,
        log_repo=sqlite,
        llm_verify=False,
    )

    assert isinstance(result, WorkoutLogResult)
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.unmatched is True
    assert entry.exercise_id is None


@pytest.mark.asyncio
async def test_multiple_entries_mixed(tmp_path, repo, fake_get_model, monkeypatch) -> None:
    """Multiple entries in one message: matched + unmatched mix."""
    from app.agents.logger import graph as logger_graph
    from app.agents.logger.graph import ParsedEntry

    async def _fake_extract(user_message: str, model) -> list[ParsedEntry]:
        return [
            ParsedEntry(raw_name="bench press", sets=3, reps=10, weight=185.0),
            ParsedEntry(raw_name="zercher good-mornings", sets=3, reps=8, weight=None),
        ]

    monkeypatch.setattr(logger_graph, "_extract_entries", _fake_extract)

    sqlite = SqliteLogRepository(tmp_path / "mixed.db")
    result = await run_logger(
        user_message="I did 3x10 bench press and 3x8 zercher good-mornings",
        session_id="session-mixed",
        repo=repo,
        log_repo=sqlite,
        llm_verify=False,
    )

    assert len(result.entries) == 2
    matched = [e for e in result.entries if not e.unmatched]
    unmatched = [e for e in result.entries if e.unmatched]
    assert len(matched) == 1
    assert len(unmatched) == 1
    assert unmatched[0].exercise_id is None


@pytest.mark.asyncio
async def test_entries_have_session_id_and_logged_at(
    tmp_path, repo, fake_get_model, monkeypatch
) -> None:
    """Every entry carries the session_id and a valid logged_at datetime."""
    from app.agents.logger import graph as logger_graph
    from app.agents.logger.graph import ParsedEntry

    async def _fake_extract(user_message: str, model) -> list[ParsedEntry]:
        return [ParsedEntry(raw_name="squat", sets=5, reps=5, weight=200.0)]

    monkeypatch.setattr(logger_graph, "_extract_entries", _fake_extract)

    sqlite = SqliteLogRepository(tmp_path / "session.db")
    result = await run_logger(
        user_message="I did 5x5 squats at 200",
        session_id="session-dt",
        repo=repo,
        log_repo=sqlite,
        llm_verify=False,
    )

    for entry in result.entries:
        assert entry.session_id == "session-dt"
        assert isinstance(entry.logged_at, datetime)
