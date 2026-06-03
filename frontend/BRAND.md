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

## Accent color — UNCONFIRMED

The `accent` token is set to `#00C2A8`, a teal/cyan-green-family default. The
exact brand hex is not exposed in source and has **not** been confirmed.

**Eyedropper pass (manual):** sample the accent from the live reference brand
surface with a color picker and update the single `accent` token in
`tailwind.config.js`. Because every component reads that one token, the
confirmed value propagates everywhere with no other change.
