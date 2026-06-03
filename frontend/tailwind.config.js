// Single source of brand tokens. All UI consumes these — no ad-hoc colors,
// fonts, or spacing values anywhere else. Structured content renders as branded
// cards built from these tokens, never as raw JSON.
//
// The `accent` hex is the documented teal-family default and is UNCONFIRMED;
// see BRAND.md for the eyedropper-confirmation step.

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#FFFFFF",
        surface: "#FAFAFA",
        "text-primary": "#1A1A1A",
        "text-secondary": "#6B7280",
        border: "#E5E7EB",
        accent: "#00C2A8", // UNCONFIRMED — teal/cyan-green family default.
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      fontSize: {
        hero: ["3.25rem", { lineHeight: "1.1", fontWeight: "700" }],
        section: ["2.25rem", { lineHeight: "1.2", fontWeight: "600" }],
        body: ["1.0625rem", { lineHeight: "1.6", fontWeight: "400" }],
      },
      fontWeight: {
        heading: "700",
        subheading: "600",
        body: "400",
      },
      borderRadius: {
        card: "0.875rem",
        button: "0.625rem",
      },
      spacing: {
        card: "1.5rem",
        section: "3rem",
      },
    },
  },
  plugins: [],
};
