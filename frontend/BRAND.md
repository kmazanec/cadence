# Brand & voice

The single source of design tokens is `tailwind.config.js`. Every component
consumes those tokens; no component hardcodes a color, font, or spacing value.
Structured content (workouts, logs) renders as branded cards — never as raw
JSON.

## Voice

Cadence speaks like a knowledgeable training partner, not a clinician or a bot.

**Do**

- Be conversational and direct — talk to the person, not at them.
- Be confident: give a clear recommendation, then the reasoning.
- Be partnership-oriented: "let's", "we", "you've got this".
- Be results-focused: tie advice to the outcome the person wants.

**Don't**

- Sound clinical, hedged, or robotic.
- Bury the answer under disclaimers.
- Dump raw data or jargon without framing it.

Assistant replies and clarification prompts both follow this voice.

### Single source of voice copy (backend)

All backend user-facing strings — the persona preamble prepended to every agent
system prompt, the clarification fallback, generator failure copy, and error
recovery — live in backend/app/voice.py. When you add copy to a backend
agent or node, import from there; never inline a new string. Each constant's
docstring explains what context it appears in.

The backend's user-facing copy is centralized in `backend/app/voice.py`
(`VOICE_PREAMBLE`, `clarification_fallback`, `GENERATOR_FAILURE_MESSAGE`,
`RECOVERY_ERROR_MESSAGE`) so every surface speaks with one voice.

## Accent color — UNCONFIRMED

The `accent` token is set to `#00C2A8`, a teal/cyan-green-family default. The
exact brand hex is not exposed in source and has **not** been confirmed.

**Eyedropper pass (manual):** sample the accent from the live reference brand
surface with a color picker and update the single `accent` token in
`tailwind.config.js`. Because every component reads that one token, the
confirmed value propagates everywhere with no other change.
