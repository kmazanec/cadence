"""Unit tests for the injury-extraction helper.

The helper is deterministic (no LLM): it maps free-text injury descriptions onto
the controlled joint vocabulary used by the repository's contraindication check.
These tests confirm that the synonym map covers common phrasings and that the
function returns [] when no injury is mentioned.
"""

from __future__ import annotations

import pytest

from app.agents.generator.injury_extraction import extract_injuries


@pytest.mark.parametrize("message,expected", [
    # Direct joint names
    ("my knee hurts", ["knee"]),
    ("knee pain", ["knee"]),
    ("I have a knee injury", ["knee"]),
    ("knee problem", ["knee"]),
    # Synonyms for knee
    ("I have patellar pain", ["knee"]),
    ("ACL injury", ["knee"]),
    ("MCL sprain", ["knee"]),
    ("meniscus tear", ["knee"]),
    # Shoulder
    ("my shoulder is sore", ["shoulder"]),
    ("rotator cuff issue", ["shoulder"]),
    ("shoulder impingement", ["shoulder"]),
    # Hip
    ("hip pain", ["hip"]),
    ("hip flexor tightness", ["hip"]),
    # Ankle
    ("sprained ankle", ["ankle"]),
    ("ankle injury", ["ankle"]),
    # Elbow
    ("tennis elbow", ["elbow"]),
    ("elbow pain", ["elbow"]),
    # Wrist
    ("wrist pain", ["wrist"]),
    ("carpal tunnel", ["wrist"]),
    # Spine synonyms
    ("lower back pain", ["lumbar spine"]),
    ("low back injury", ["lumbar spine"]),
    ("lumbar pain", ["lumbar spine"]),
    ("neck pain", ["cervical spine"]),
    ("cervical injury", ["cervical spine"]),
    # No injury mentioned
    ("give me an upper body workout", []),
    ("", []),
    ("I want to work on my glutes", []),
    ("full body workout please", []),
])
def test_extract_injuries_parametrized(message: str, expected: list[str]) -> None:
    """Confirm the synonym map covers common injury phrasings."""
    result = extract_injuries(message)
    assert sorted(result) == sorted(expected), (
        f"extract_injuries({message!r}) = {result!r}, expected {expected!r}"
    )


def test_extract_injuries_is_deterministic() -> None:
    """Calling extract_injuries twice with the same input returns the same result."""
    msg = "I have knee and shoulder pain"
    first = extract_injuries(msg)
    second = extract_injuries(msg)
    assert first == second


def test_extract_injuries_multiple_joints() -> None:
    """A message mentioning multiple joints returns all of them."""
    result = extract_injuries("knee and hip injury")
    assert "knee" in result
    assert "hip" in result
    assert len(result) == 2


def test_extract_injuries_no_llm_call(monkeypatch) -> None:
    """extract_injuries must not call get_model (must remain deterministic)."""
    called = []

    def _fail_if_called(role):
        called.append(role)
        raise AssertionError("extract_injuries must not call get_model")

    monkeypatch.setattr("app.models.factory.get_model", _fail_if_called)
    result = extract_injuries("my knee hurts")
    assert not called, "extract_injuries must not invoke the LLM"
    assert result == ["knee"]


@pytest.mark.parametrize("message", [
    # "fai" (hip) must not match "fairly", "fair", "fail", "faint"
    "a fairly intense workout",
    "fair warning",
    "fail",
    "faint",
    # "hip" must not match "championship" or "relationship"
    "championship training",
    "relationship goals workout",
    # "acl" (knee) must not match "obstacle"
    "give me an obstacle course style workout",
    # "neck" (cervical spine) must not match "bottleneck"
    "bottleneck",
])
def test_extract_injuries_no_false_positives(message: str) -> None:
    """Common non-injury words that share substrings with synonym patterns must not trigger extraction."""
    result = extract_injuries(message)
    assert result == [], (
        f"extract_injuries({message!r}) = {result!r}, expected [] (false positive)"
    )
