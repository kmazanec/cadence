/**
 * CadenceMark — the brand logo: a pulse / sound-wave / rep-tempo waveform.
 *
 * One line that reads three ways at once — a heartbeat, an audio wave, and the
 * rise-and-fall of training intensity. When `animated`, the line draws itself
 * on a loop (the same motif the "thinking" indicator reuses).
 *
 * Pure presentation; colors come from brand tokens via `currentColor`, so the
 * caller sets the hue with a text-color utility.
 */

interface CadenceMarkProps {
  size?: number;
  animated?: boolean;
  className?: string;
  strokeWidth?: number;
}

export function CadenceMark({
  size = 28,
  animated = false,
  className = "",
  strokeWidth = 2.5,
}: CadenceMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      {/* The cadence waveform: flat → spike → rhythm → flat. */}
      <path
        d="M2 20 H9 L13 20 L16 8 L20 32 L24 14 L27 24 L31 20 H38"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={animated ? 120 : undefined}
        className={animated ? "animate-pulse-dash" : undefined}
      />
    </svg>
  );
}

/**
 * CadenceWordmark — the mark locked up with the "Cadence" wordmark.
 * Used in the app header.
 */
export function CadenceWordmark({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <span className="grid h-9 w-9 place-items-center rounded-button bg-ink text-accent-volt shadow-glow">
        <CadenceMark size={22} strokeWidth={3} />
      </span>
      <span className="font-heading text-[1.35rem] leading-none text-ink">
        Cadence
      </span>
    </div>
  );
}
