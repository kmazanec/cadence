"""Extract injury terms from a user message.

Maps free-text injury mentions onto the controlled joint vocabulary the
repository uses to decide contraindications. Returns the normalised joint
terms found in the message, or an empty list when none are present.

The synonym map covers the joint vocabulary present in the exercise dataset:
shoulder, elbow, wrist, knee, hip, cervical spine, ankle, thoracic spine,
lumbar spine. Each entry maps one or more common English phrasings onto the
canonical joint name. Matching is case-insensitive; all patterns use a leading
word-boundary anchor so they cannot fire mid-word (e.g. "hip" cannot match
inside "championship", "neck" cannot match inside "bottleneck"). Patterns that
are complete words or abbreviations (not intentional prefixes) also use a
trailing word-boundary anchor so "fai" cannot match "fairly", "acl" cannot
match "obstacle".

This function is deterministic and makes no LLM call — it is safe to call on
every request without incurring inference cost or nondeterminism. This is a
deliberate design choice: the safety invariant (no knee-loading exercise for a
knee injury) must not depend on a stochastic model call.
"""

from __future__ import annotations

import re

# Maps lowercase patterns to the canonical joint vocabulary term.  Each entry
# is a tuple of (pattern, is_prefix): when is_prefix is True the pattern is
# the start of a medical term (e.g. "patell" matches "patellar"/"patella") and
# only a leading \b is applied; when False (complete word/abbreviation) both
# leading and trailing \b are applied so the pattern cannot match inside a
# longer unrelated word.
_SYNONYM_MAP: dict[str, list[tuple[str, bool]]] = {
    "knee": [
        ("knee", False),
        ("patell", True),       # patellar, patella
        ("acl", False),
        ("mcl", False),
        ("pcl", False),
        ("lcl", False),
        ("meniscus", False),
        ("menisci", False),
        ("cruciate", False),
        ("kneecap", False),
    ],
    "shoulder": [
        ("shoulder", False),
        ("rotator cuff", False),
        ("labrum", False),
        ("labral", False),
        ("glenohumeral", False),
        ("acromi", True),        # acromioclavicular, acromion
        ("impingement", False),
        ("clavicle", False),
    ],
    "hip": [
        ("hip", False),
        ("hip flexor", False),
        ("iliotibial", False),
        ("it band", False),
        ("groin", False),
        ("trochanter", False),
        ("fai", False),          # femoroacetabular impingement
        ("piriformis", False),
    ],
    "ankle": [
        ("ankle", False),
        ("achilles", False),
        ("plantar fasci", True),
        ("plantar", False),
        ("peroneal", False),
        ("ankle sprain", False),
    ],
    "elbow": [
        ("elbow", False),
        ("tennis elbow", False),
        ("golfer", False),       # golfer's elbow
        ("epicondyl", True),     # lateral/medial epicondylitis
        ("olecranon", False),
        ("cubital", False),
    ],
    "wrist": [
        ("wrist", False),
        ("carpal tunnel", False),
        ("carpal", False),
        ("scaphoid", False),
        ("tfcc", False),         # triangular fibrocartilage complex
        ("de quervain", False),
    ],
    "lumbar spine": [
        ("lower back", False),
        ("low back", False),
        ("lumbar", False),
        ("lumbosacral", False),
        ("herniated disc", False),
        ("disc herniat", True),
        ("bulging disc", False),
        ("sciatica", False),
        ("spondyl", True),       # spondylolisthesis, spondylosis
    ],
    "cervical spine": [
        ("cervical", False),
        ("whiplash", False),
        ("neck", False),
    ],
    "thoracic spine": [
        ("thoracic", False),
        ("mid back", False),
        ("middle back", False),
        ("kyphosis", False),
    ],
}


def _compile_pattern(pat: str, is_prefix: bool) -> re.Pattern[str]:
    """Return a compiled regex for *pat* with appropriate word-boundary anchors.

    All patterns get a leading \\b so they cannot match mid-word.  Complete
    words/abbreviations (is_prefix=False) also get a trailing \\b so they
    cannot match as a prefix of a longer unrelated word.
    """
    escaped = re.escape(pat)
    if is_prefix:
        return re.compile(r"\b" + escaped)
    return re.compile(r"\b" + escaped + r"\b")


# Pre-compile one regex per pattern for efficiency.
_COMPILED_MAP: dict[str, list[re.Pattern[str]]] = {
    joint: [_compile_pattern(pat, is_prefix) for pat, is_prefix in entries]
    for joint, entries in _SYNONYM_MAP.items()
}


def extract_injuries(message: str) -> list[str]:
    """Return the injury/joint terms mentioned in *message*.

    Scans the lowercased message for each synonym in the map and collects the
    canonical joint terms that match. The returned list contains unique terms
    from the closed joint vocabulary. An empty list means no injury was
    detected and the request is unconstrained.
    """
    lowered = message.casefold()
    found: set[str] = set()
    for joint, patterns in _COMPILED_MAP.items():
        if any(pat.search(lowered) for pat in patterns):
            found.add(joint)
    return sorted(found)
