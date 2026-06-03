"""Extract injury terms from a user message.

Maps free-text injury mentions onto the controlled joint vocabulary the
repository uses to decide contraindications. Returns the normalised joint
terms found in the message, or an empty list when none are present.

The synonym map covers the joint vocabulary present in the exercise dataset:
shoulder, elbow, wrist, knee, hip, cervical spine, ankle, thoracic spine,
lumbar spine. Each entry maps one or more common English phrasings onto the
canonical joint name. Matching is case-insensitive and substring-based.

This function is deterministic and makes no LLM call — it is safe to call on
every request without incurring inference cost or nondeterminism. This is a
deliberate design choice: the safety invariant (no knee-loading exercise for a
knee injury) must not depend on a stochastic model call.
"""

from __future__ import annotations

# Maps lowercase substring patterns to the canonical joint vocabulary term.
# Patterns are checked as substrings of the lowercased message. Longer and
# more-specific patterns appear first in each list so they can be extended
# without ambiguity; the matching is a set-union over all patterns per joint.
_SYNONYM_MAP: dict[str, list[str]] = {
    "knee": [
        "knee",
        "patell",       # patellar, patella
        "acl",
        "mcl",
        "pcl",
        "lcl",
        "meniscus",
        "menisci",
        "cruciate",
        "kneecap",
    ],
    "shoulder": [
        "shoulder",
        "rotator cuff",
        "labrum",
        "labral",
        "glenohumeral",
        "acromi",        # acromioclavicular, acromion
        "impingement",
        "clavicle",
    ],
    "hip": [
        "hip",
        "hip flexor",
        "iliotibial",
        "it band",
        "groin",
        "trochanter",
        "fai",           # femoroacetabular impingement
        "piriformis",
    ],
    "ankle": [
        "ankle",
        "achilles",
        "plantar fasci",
        "plantar",
        "peroneal",
        "ankle sprain",
    ],
    "elbow": [
        "elbow",
        "tennis elbow",
        "golfer",        # golfer's elbow
        "epicondyl",     # lateral/medial epicondylitis
        "olecranon",
        "cubital",
    ],
    "wrist": [
        "wrist",
        "carpal tunnel",
        "carpal",
        "scaphoid",
        "tfcc",          # triangular fibrocartilage complex
        "de quervain",
    ],
    "lumbar spine": [
        "lower back",
        "low back",
        "lumbar",
        "lumbosacral",
        "herniated disc",
        "disc herniat",
        "bulging disc",
        "sciatica",
        "spondyl",       # spondylolisthesis, spondylosis
    ],
    "cervical spine": [
        "cervical",
        "whiplash",
        "neck",
    ],
    "thoracic spine": [
        "thoracic",
        "mid back",
        "middle back",
        "kyphosis",
    ],
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
    for joint, patterns in _SYNONYM_MAP.items():
        if any(pattern in lowered for pattern in patterns):
            found.add(joint)
    return sorted(found)
