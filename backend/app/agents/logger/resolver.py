"""Exercise name resolver for the logger.

Resolves a raw user-typed exercise name to a catalogue exercise, using
RapidFuzz WRatio (cutoff 80) to produce a shortlist, then optionally asking
the model to pick the best match from that shortlist.

When ``llm_verify=True`` (the default), the model confirms the top candidate
if the fuzzy score is ambiguous; this lets the model handle abbreviations and
colloquialisms that pure string similarity misses. The LLM step uses
``get_model('logger')`` and is toggled off in tests via ``llm_verify=False``.

Returns ``(exercise_id, exercise_name)`` when matched, ``None`` when
unresolvable — never an invented or arbitrary substitution.
"""

from __future__ import annotations

from rapidfuzz import fuzz, process

from app.data.repository import Exercise, ExerciseRepository

# Minimum WRatio score to consider a candidate. Below 80 the match is too
# speculative to record as a confirmed exercise.
_WRATIO_CUTOFF = 80

# Number of shortlist candidates to pass to the LLM verify step.
_SHORTLIST_SIZE = 5

# Sentinel returned by _llm_verify when the model was successfully consulted
# but explicitly chose pick==0 (no good match).  Distinct from None, which
# means the LLM call failed and we should fall back to the fuzzy top result.
_DECLINED: object = object()


def _build_name_corpus(
    repo: ExerciseRepository,
) -> dict[str, Exercise]:
    """Return a mapping of lowercase name -> Exercise for the full catalogue."""
    return {ex.name.casefold(): ex for ex in repo.all()}


def resolve_exercise_name(
    raw_name: str,
    repo: ExerciseRepository,
    *,
    llm_verify: bool = True,
) -> tuple[str, str] | None:
    """Resolve ``raw_name`` to a ``(exercise_id, exercise_name)`` pair.

    Performs a RapidFuzz WRatio scan over the full exercise catalogue. If
    ``llm_verify`` is True and a shortlist exists, the model picks the best
    match. Returns ``None`` when no candidate clears the cutoff or when the
    model explicitly declines — guaranteeing the caller never receives an
    invented exercise.

    LLM verify tri-state:
    - Returns a name string  -> model selected a candidate; use it.
    - Returns ``_DECLINED``  -> model was reached but chose pick==0; return None.
    - Returns ``None``       -> LLM call failed; fall back to fuzzy top result.
    """
    if not raw_name or not raw_name.strip():
        return None

    corpus = _build_name_corpus(repo)
    query = raw_name.casefold().strip()

    candidates = process.extract(
        query,
        list(corpus.keys()),
        scorer=fuzz.WRatio,
        limit=_SHORTLIST_SIZE,
        score_cutoff=_WRATIO_CUTOFF,
    )

    if not candidates:
        return None

    # Best candidate by score (process.extract returns descending order).
    best_name, best_score, _ = candidates[0]

    if llm_verify and len(candidates) > 0:
        verified = _llm_verify(raw_name, candidates, corpus)
        if verified is _DECLINED:
            # Model was successfully consulted and explicitly rejected all
            # candidates — honour that decision rather than accepting the
            # fuzzy top match.
            return None
        if verified is not None:
            ex = corpus[verified]
            return ex.id, ex.name
        # verified is None: LLM call failed; fall through to fuzzy top result.

    ex = corpus[best_name]
    return ex.id, ex.name


def _llm_verify(
    raw_name: str,
    candidates: list[tuple[str, float, int]],
    corpus: dict[str, Exercise],
) -> object:
    """Ask the model to pick the best match from the shortlist.

    Returns:
    - The lowercase exercise name from ``corpus`` that the model selected.
    - ``_DECLINED`` sentinel when the model was reached and chose pick==0
      (no good match among the shortlist).
    - ``None`` when the LLM call raised an exception (best-effort fallback).
    """
    import app.models.factory as _factory
    from langchain_core.messages import HumanMessage, SystemMessage
    from pydantic import BaseModel

    from app.models.config import MODEL_CONFIG
    from app.observability import logging as obs

    shortlist = [name for name, _score, _idx in candidates]
    numbered = "\n".join(f"{i+1}. {name}" for i, name in enumerate(shortlist))

    system_prompt = (
        "You are an exercise name resolver. "
        "Given a user's typed exercise name and a numbered shortlist of "
        "catalogue matches, reply with ONLY the number of the best match "
        "(1-based). If none is a good match for the user's exercise, reply "
        "with 0."
    )
    user_prompt = (
        f"User typed: \"{raw_name}\"\n\n"
        f"Shortlist:\n{numbered}\n\n"
        "Reply with the number only."
    )

    try:
        model = _factory.get_model("logger")

        class _Pick(BaseModel):
            pick: int

        structured = model.with_structured_output(_Pick)
        with obs.llm_call("logger", MODEL_CONFIG["logger"]):
            result: _Pick = structured.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        pick = result.pick
        if pick == 0:
            # Model explicitly indicated no candidate is a good match.
            return _DECLINED
        if 1 <= pick <= len(shortlist):
            return shortlist[pick - 1]
        # Out-of-range pick: treat as a failed/nonsensical response.
        return None
    except Exception:
        # LLM verify is best-effort; fall through to fuzzy top result.
        pass

    return None
