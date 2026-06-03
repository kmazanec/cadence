// Single source of brand tokens. All UI consumes these — no ad-hoc colors,
// fonts, or spacing values anywhere else. Structured content renders as branded
// cards built from these tokens, never as raw JSON.
//
// BRAND: "Cadence — find your rhythm." Energetic & athletic, on a bright canvas.
// The energy comes from a bold volt/teal accent system, condensed display type,
// and kinetic motion — not from a dark background. Premium-athletic-but-daylit.

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Bright, slightly warm athletic canvas (not pure clinical white).
        canvas: "#F6F7F3",
        background: "#FFFFFF",
        surface: "#FFFFFF",
        "surface-sunken": "#EFF1EC",

        // Near-black ink with a hint of green so it sits in the brand family.
        ink: "#10140F",
        "text-primary": "#10140F",
        "text-secondary": "#5E665A",
        "text-muted": "#7C8475",
        border: "#E2E6DC",
        "border-strong": "#CBD1C2",

        // Accent system. `accent` stays the single canonical token every legacy
        // component reads; volt + teal give it range for gradients and glows.
        accent: "#00C2A8", // canonical teal (UNCONFIRMED per BRAND.md eyedropper).
        "accent-volt": "#C6F432", // electric lime — the "go" color.
        "accent-deep": "#0A7E6E", // deep teal for text-on-light contrast.
        "accent-ink": "#04201C", // text placed on a volt/teal fill.
      },
      fontFamily: {
        // Body — warm, legible grotesque.
        sans: [
          "Hanken Grotesk",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        // Display — muscular athletic grotesque for headers, numerals, labels.
        display: [
          "Archivo",
          "ui-sans-serif",
          "system-ui",
          "Segoe UI",
          "sans-serif",
        ],
      },
      fontSize: {
        hero: ["3.25rem", { lineHeight: "1.04", fontWeight: "800" }],
        section: ["2.25rem", { lineHeight: "1.1", fontWeight: "700" }],
        body: ["1.0625rem", { lineHeight: "1.6", fontWeight: "400" }],
      },
      fontWeight: {
        heading: "800",
        subheading: "600",
        body: "400",
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      borderRadius: {
        card: "1.125rem",
        button: "0.75rem",
        pill: "999px",
      },
      spacing: {
        card: "1.5rem",
        section: "3rem",
      },
      boxShadow: {
        // Soft athletic lift — never harsh.
        card: "0 1px 2px rgba(16,20,15,0.04), 0 12px 28px -16px rgba(16,20,15,0.18)",
        "card-hover":
          "0 2px 4px rgba(16,20,15,0.05), 0 22px 44px -20px rgba(16,20,15,0.24)",
        glow: "0 8px 24px -8px rgba(0,194,168,0.55)",
        "glow-volt": "0 8px 24px -8px rgba(170,214,40,0.6)",
      },
      backgroundImage: {
        "accent-sweep": "linear-gradient(100deg, #00C2A8 0%, #1FD3A0 55%, #C6F432 130%)",
        "volt-sweep": "linear-gradient(105deg, #C6F432 0%, #5BE6B0 100%)",
      },
      keyframes: {
        "rise-in": {
          "0%": { opacity: "0", transform: "translateY(8px) scale(0.99)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        "pulse-dash": {
          // The logo waveform / "thinking" line drawing itself.
          "0%": { strokeDashoffset: "120" },
          "100%": { strokeDashoffset: "0" },
        },
        "tempo-bounce": {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1)" },
        },
        "sheen": {
          "0%": { transform: "translateX(-120%)" },
          "100%": { transform: "translateX(220%)" },
        },
      },
      animation: {
        "rise-in": "rise-in 0.34s cubic-bezier(0.16,1,0.3,1) both",
        "pulse-dash": "pulse-dash 1.4s ease-in-out infinite alternate",
        "tempo-bounce": "tempo-bounce 0.9s ease-in-out infinite",
        sheen: "sheen 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
