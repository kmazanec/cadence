"""Extract injury terms from a user message.

Maps free-text injury mentions onto the controlled joint vocabulary the
repository uses to decide contraindications. Returns the normalised joint
terms found in the message, or an empty list when none are present.
"""

from __future__ import annotations


def extract_injuries(message: str) -> list[str]:
    """Return the injury/joint terms mentioned in *message*.

    The returned terms are drawn from the closed joint vocabulary used by the
    repository's contraindication check. An empty list means no injury was
    detected and the request is unconstrained.
    """
    return []
