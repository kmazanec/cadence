"""Static capability registry for the models the config may reference, plus the
startup validation that refuses to run on a misconfigured role.
"""

from __future__ import annotations

from pydantic import BaseModel

from .config import MODEL_CONFIG, STRUCTURED_OUTPUT_ROLES, Role


class ModelCapability(BaseModel):
    supports_structured_output: bool
    supports_tools: bool
    context_window: int
    notes: str


# Known models and what they can do. A model absent from this registry is
# treated as unverified and rejected for structured-output roles.
REGISTRY: dict[str, ModelCapability] = {
    "openai/gpt-4o-mini": ModelCapability(
        supports_structured_output=True,
        supports_tools=True,
        context_window=128_000,
        notes="Shared capable default; structured output and tool calling.",
    ),
    "openai/gpt-4o": ModelCapability(
        supports_structured_output=True,
        supports_tools=True,
        context_window=128_000,
        notes="Higher-capability alternative for any role.",
    ),
}


def validate_model_config(config: dict[Role, str] | None = None) -> None:
    """Fail fast if any structured-output role maps to an unknown or incapable model.

    Raises:
        ValueError: when a structured-output role's model is missing from the
            registry or lacks structured-output support.
    """

    config = config if config is not None else MODEL_CONFIG
    for role in STRUCTURED_OUTPUT_ROLES:
        model_id = config.get(role)
        if model_id is None:
            raise ValueError(f"No model configured for role '{role}'.")
        capability = REGISTRY.get(model_id)
        if capability is None:
            raise ValueError(
                f"Role '{role}' maps to unknown model '{model_id}'; "
                "add it to the capability registry before use."
            )
        if not capability.supports_structured_output:
            raise ValueError(
                f"Role '{role}' requires structured output, but model "
                f"'{model_id}' does not support it."
            )
