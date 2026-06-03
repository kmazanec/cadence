"""Critical-path #4: logger fuzzy-match resolve-or-flag (no LLM).

Rationale (ADR-018, priority #4):
  The logger must never invent an exercise: if a fuzzy match is found at
  WRatio >= 80 it records the catalogue exercise ID; if no candidate clears
  the cutoff the entry is flagged ``unmatched=True`` and included as-is.
  This property must hold deterministically — no LLM, no network — because
  RapidFuzz WRatio is pure Python and the cutoff is a hard invariant.

Architecture risks pinned:
  1. A matched entry must carry a real dataset exercise_id — never a string
     that was invented or copied directly from the user's typed name.
  2. An unmatched entry must have unmatched=True, exercise_id=None, and must
     NOT have an invented exercise_id.
  3. Persisted entries are retrievable via LogRepository.for_session against
     SQLite (the offline-default backend), confirming the full write path.

The llm_verify=False kwarg disables the LLM confirmation step so the test
runs offline without any OPENROUTER_API_KEY.
"""

from __future__ import annotations

from app.agents.logger.resolver import resolve_exercise_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_repo():
    from app.data.json_repository import JsonExerciseRepository

    return JsonExerciseRepository()


def _all_exercise_ids(repo) -> set[str]:
    return {ex.id for ex in repo.all()}


# ---------------------------------------------------------------------------
# Fuzzy-match resolution (WRatio >= 80 → real ID)
# ---------------------------------------------------------------------------


def test_bench_press_resolves_to_dataset_id():
    """'bench press' resolves to a real catalogue exercise ID (WRatio >= 80).

    The canonical ADR-018 example: a common exercise name typed casually should
    map to a catalogue entry, not return None or an invented ID.
    """
    repo = _build_repo()
    known_ids = _all_exercise_ids(repo)

    result = resolve_exercise_name("bench press", repo, llm_verify=False)

    assert result is not None, (
        "Expected 'bench press' to resolve to a catalogue exercise, got None"
    )
    exercise_id, exercise_name = result
    assert exercise_id in known_ids, (
        f"Resolved exercise_id {exercise_id!r} is not in the dataset "
        f"(name returned: {exercise_name!r})"
    )
    assert exercise_name, "Resolved exercise_name must not be empty"


def test_barbell_bench_resolves_to_dataset_id():
    """'barbell bench' (abbreviated) also resolves to a real catalogue ID."""
    repo = _build_repo()
    known_ids = _all_exercise_ids(repo)

    result = resolve_exercise_name("barbell bench", repo, llm_verify=False)
    assert result is not None, "Expected 'barbell bench' to resolve"
    exercise_id, _name = result
    assert exercise_id in known_ids, f"Resolved ID {exercise_id!r} not in dataset"


def test_push_up_resolves_to_dataset_id():
    """'push up' / 'push-up' resolves to a real catalogue exercise."""
    repo = _build_repo()
    known_ids = _all_exercise_ids(repo)

    result = resolve_exercise_name("push up", repo, llm_verify=False)
    assert result is not None, "Expected 'push up' to resolve"
    exercise_id, _name = result
    assert exercise_id in known_ids


# ---------------------------------------------------------------------------
# Unresolvable name → flagged unmatched, never invented
# ---------------------------------------------------------------------------


def test_zercher_good_mornings_is_unmatched():
    """'zercher good-mornings' is not in the dataset — must return None (unmatched).

    The canonical ADR-018 unmatchable example: an unusual variation that is not
    in the exercise catalogue must NOT be mapped to an invented or closest-match
    exercise. Returning None forces the caller to flag it unmatched.
    """
    repo = _build_repo()

    result = resolve_exercise_name("zercher good-mornings", repo, llm_verify=False)

    assert result is None, (
        f"Expected None for an unmatchable exercise, but got {result!r}. "
        "The resolver must not invent or substitute a dataset exercise."
    )


def test_completely_nonsensical_name_is_unmatched():
    """A clearly nonsensical name produces None, not an invented ID."""
    repo = _build_repo()
    result = resolve_exercise_name("xzqvpk florbulator", repo, llm_verify=False)
    assert result is None, (
        f"Expected None for nonsensical input, got {result!r}"
    )


def test_empty_name_is_unmatched():
    """An empty name produces None without raising."""
    repo = _build_repo()
    result = resolve_exercise_name("", repo, llm_verify=False)
    assert result is None


def test_whitespace_name_is_unmatched():
    """A whitespace-only name produces None without raising."""
    repo = _build_repo()
    result = resolve_exercise_name("   ", repo, llm_verify=False)
    assert result is None


# ---------------------------------------------------------------------------
# LogEntry creation and persistence (write path, SQLite)
# ---------------------------------------------------------------------------


def test_matched_entry_persisted_retrievable(tmp_path):
    """A matched log entry is persisted and retrievable via LogRepository.for_session.

    Uses a temp SQLite database to avoid polluting the development DB.
    The entry's exercise_id must be a real dataset ID — not the raw name.
    """
    from app.data.sqlite_log_repository import SqliteLogRepository

    # Pass the file path (not a SQLAlchemy URL) — the repository adds sqlite:/// itself.
    log_repo = SqliteLogRepository(tmp_path / "test_log.db")

    from datetime import datetime, timezone

    from app.data.log_repository import LogEntry

    repo = _build_repo()
    known_ids = _all_exercise_ids(repo)

    result = resolve_exercise_name("bench press", repo, llm_verify=False)
    assert result is not None
    exercise_id, _exercise_name = result

    session = "sess-persist-test"
    entry = LogEntry(
        session_id=session,
        exercise_id=exercise_id,
        raw_name="bench press",
        sets=3,
        reps=10,
        weight=135.0,
        unmatched=False,
        logged_at=datetime.now(timezone.utc),
    )

    log_repo.append([entry], session)

    retrieved = log_repo.for_session(session)
    assert len(retrieved) == 1, f"Expected 1 entry, got {len(retrieved)}"

    saved = retrieved[0]
    assert saved.exercise_id in known_ids, (
        f"Persisted exercise_id {saved.exercise_id!r} is not in the dataset"
    )
    assert not saved.unmatched
    assert saved.raw_name == "bench press"
    assert saved.sets == 3
    assert saved.reps == 10


def test_unmatched_entry_persisted_with_flag(tmp_path):
    """An unmatched entry is persisted with unmatched=True, exercise_id=None."""
    from datetime import datetime, timezone

    from app.data.log_repository import LogEntry
    from app.data.sqlite_log_repository import SqliteLogRepository

    log_repo = SqliteLogRepository(tmp_path / "test_unmatched.db")

    session = "sess-unmatched-test"
    entry = LogEntry(
        session_id=session,
        exercise_id=None,
        raw_name="zercher good-mornings",
        sets=None,
        reps=None,
        weight=None,
        unmatched=True,
        logged_at=datetime.now(timezone.utc),
    )

    log_repo.append([entry], session)
    retrieved = log_repo.for_session(session)
    assert len(retrieved) == 1

    saved = retrieved[0]
    assert saved.unmatched is True
    assert saved.exercise_id is None
    assert saved.raw_name == "zercher good-mornings"


# ---------------------------------------------------------------------------
# Injury hard-exclusion note (ADR-018 #2)
# ---------------------------------------------------------------------------
# Injury hard-exclusion (ADR-018 critical path #2) covers the
# injury-avoidance capability. The generator does not yet integrate the
# contraindicated_ids() repository method into the workout-generation loop;
# the field exists on GeneratorState and in the repository, but the generator
# graph passes injuries=[] and does not filter by contraindicated IDs.
#
# This omission is documented as an explicit decision: the injury-exclusion
# safety path is not yet wired into the generator loop. The output-gate tests
# in test_recovery_no_hallucination.py cover the safety-critical determinism
# intent of ADR-018 #2.
#
# The contraindicated_ids() method is exercised directly here as a unit test
# confirming the data layer's correctness. Injury hard-exclusion is not yet
# wired into the generator loop; this is a repository-layer unit test
# confirming contraindicated_ids() data correctness.


def test_contraindicated_ids_excludes_knee_loading():
    """contraindicated_ids('knee') returns a non-empty set of excluded IDs.

    This is a repository-layer unit test confirming the data plumbing is
    correct. It does NOT test the generator subgraph integrating these IDs;
    injury hard-exclusion is not yet wired into the generator loop.
    """
    repo = _build_repo()
    excluded = repo.contraindicated_ids(["knee"])
    known_ids = _all_exercise_ids(repo)

    # Should exclude some exercises.
    assert len(excluded) > 0, (
        "Expected at least one exercise to be contraindicated for 'knee' injury; "
        "check that exercises.json contains exercises with 'knee' in joints_loaded"
    )

    # All excluded IDs must be real dataset IDs (not invented).
    invented = excluded - known_ids
    assert not invented, f"contraindicated_ids returned non-dataset IDs: {invented}"
