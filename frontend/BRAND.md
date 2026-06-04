# Cadence — brand & voice

> **Find your rhythm.**

The single source of design tokens is `tailwind.config.js`. Every component
consumes those tokens; no component hardcodes a color, font, or spacing value.
Structured content (workouts, logs) renders as branded cards — never as raw
JSON.

## Concept

Cadence is the tempo of consistent training — the rhythm you build, rep by rep,
day by day. The aesthetic is **energetic & athletic on a bright canvas**: the
energy comes from a bold volt/teal accent system, condensed display type, and
kinetic motion — *not* from a dark theme. Premium-athletic, but daylit.

The **mark** is a pulse / sound-wave / rep-tempo waveform (`CadenceMark`) — one
line that reads as a heartbeat, an audio wave, and the rise-and-fall of training
intensity at once. It animates (draws itself) for "thinking" and live states.

## Type

- **Display — Archivo** (700–900): muscular athletic grotesque for headers,
  the wordmark, numerals, and uppercase labels. Tracked tight (`-0.04em`).
- **Body — Hanken Grotesk**: warm, highly legible. All prose and inputs.

Loaded in `index.html`; mapped to `font-display` / `font-sans` (and the
`font-heading` / `font-subheading` component classes) in the token layer.

## Color

| Token            | Hex       | Use                                            |
| ---------------- | --------- | ---------------------------------------------- |
| `canvas`         | `#F6F7F3` | App background (warm off-white + faint grid).  |
| `surface`        | `#FFFFFF` | Cards, composer.                               |
| `surface-sunken` | `#EFF1EC` | Banners, inert chips.                          |
| `ink`            | `#10140F` | Primary text + logo chip (near-black, green-cast). |
| `accent`         | `#00C2A8` | Canonical teal — **UNCONFIRMED** (see below).  |
| `accent-volt`    | `#C6F432` | Electric lime — the "go" color (mark, accents).|
| `accent-deep`    | `#0A7E6E` | Teal for text/icons on light (AA contrast).    |
| `accent-ink`     | `#04201C` | Text placed on a volt/teal fill.               |

The primary action and the user's own messages use `surface-accent` — the
`accent-sweep` teal→volt gradient. This is the brand's signature fill.

### Accent color — UNCONFIRMED

`accent` is `#00C2A8`, a teal/cyan-green default; the exact brand hex has **not**
been confirmed. **Eyedropper pass (manual):** sample the accent from the live
reference brand surface and update the single `accent` token in
`tailwind.config.js`; it propagates everywhere. The volt/deep/ink companions are
derived to pair with whatever `accent` lands on.

## Motion

Kinetic but restrained, and `prefers-reduced-motion`-aware (looping animations
disable). Signature moments:

- **`pulse-dash`** — the mark draws itself; used for the coach avatar while
  streaming and the empty-state hero.
- **`tempo-bounce`** — four bars keeping a beat; the "thinking" indicator and
  the send button's busy state.
- **`rise-in`** — staggered entrance for messages and the hero.
- **`sheen` / glows** — soft accent glow on the primary action and accent fills.

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

Assistant replies and clarification prompts both follow this voice. UI copy
matches it too: "Let's build something today.", "Finding your rhythm…".

### Single source of voice copy (backend)

All backend user-facing strings — the persona preamble prepended to every agent
system prompt, the clarification fallback, generator failure copy, and error
recovery — live in backend/app/voice.py. When you add copy to a backend
agent or node, import from there; never inline a new string. Each constant's
docstring explains what context it appears in.

## Chrome

Chat-first with light chrome (no full nav):

- `AppHeader` — wordmark + time-aware greeting, plus illustrative stats (streak
  flame, weekly progress ring). Stats are non-functional chrome that make
  Cadence read as a coaching product, not a bare chatbox.
- `QuickActions` — three chips (build / log / ask) mapping to the three
  sub-agent routes; they prefill the composer, they don't call the API.
- Composer — auto-sizing textarea (Enter sends, Shift+Enter newlines) with the
  signature gradient send button.
