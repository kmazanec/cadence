/**
 * QuickActions — the three things Cadence does, as one-tap chips that prefill
 * the composer. They map to the three sub-agent routes (coach / generate / log)
 * but stay UI-only: they hand text to the input, they don't call the API.
 */

export interface QuickAction {
  label: string;
  icon: string;
  prompt: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    label: "Build a workout",
    icon: "🏋️",
    prompt: "Build me a 45-minute full-body workout with dumbbells.",
  },
  {
    label: "Log a session",
    icon: "✅",
    prompt: "Log: 3 sets of 8 bench press at 135, then 3x10 rows.",
  },
  {
    label: "Ask the coach",
    icon: "💬",
    prompt: "How many rest days should I take each week?",
  },
];

export function QuickActions({
  onPick,
  disabled,
}: {
  onPick: (prompt: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {QUICK_ACTIONS.map((a) => (
        <button
          key={a.label}
          type="button"
          disabled={disabled}
          onClick={() => onPick(a.prompt)}
          className="group flex items-center gap-2 rounded-pill border border-border-strong bg-surface px-3.5 py-2 text-sm font-medium text-text-primary shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent-deep hover:text-accent-deep hover:shadow-card disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        >
          <span aria-hidden="true">{a.icon}</span>
          {a.label}
        </button>
      ))}
    </div>
  );
}
