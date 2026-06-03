/**
 * AppHeader — branded chat-first chrome.
 *
 * Logo + a time-aware greeting on the left; a row of "this is a real fitness
 * product" stats on the right (streak flame, weekly ring, minutes). The stats
 * are illustrative chrome, not wired to data — they make Cadence read as a
 * coaching app rather than a bare chatbox.
 */

import { CadenceWordmark } from "../brand/CadenceMark";

/** A weekly-goal progress ring drawn from brand tokens. */
function WeekRing({ done, goal }: { done: number; goal: number }) {
  const pct = Math.min(done / goal, 1);
  const r = 15;
  const c = 2 * Math.PI * r;
  return (
    <span className="relative grid h-11 w-11 place-items-center">
      <svg viewBox="0 0 40 40" className="h-11 w-11 -rotate-90">
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-surface-sunken"
        />
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className="text-accent-deep transition-[stroke-dashoffset] duration-700"
        />
      </svg>
      <span className="absolute font-display text-[0.7rem] font-bold text-ink">
        {done}/{goal}
      </span>
    </span>
  );
}

function Stat({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      {icon}
      <div className="leading-none">
        <div className="font-display text-base font-extrabold text-ink">
          {value}
        </div>
        <div className="mt-0.5 text-[0.7rem] uppercase tracking-wide text-text-muted">
          {label}
        </div>
      </div>
    </div>
  );
}

export function AppHeader() {
  // Time-aware greeting — small touch that makes the partner voice feel present.
  const hour = new Date().getHours();
  const partOfDay =
    hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  return (
    <header className="shrink-0 border-b border-border bg-canvas/80 backdrop-blur-sm">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-y-3 px-5 py-3.5">
        <div>
          <CadenceWordmark />
          <p className="mt-1.5 pl-[2.9rem] text-sm text-text-secondary">
            Good {partOfDay}, Alex — let&apos;s find your rhythm.
          </p>
        </div>

        <div className="flex items-center gap-5 pl-[2.9rem] sm:pl-0">
          <Stat
            icon={
              <span
                className="text-lg"
                role="img"
                aria-label="streak"
              >
                🔥
              </span>
            }
            value="12"
            label="day streak"
          />
          <div className="hidden h-9 w-px bg-border sm:block" />
          <div className="hidden items-center gap-2 sm:flex">
            <WeekRing done={3} goal={4} />
            <div className="leading-none">
              <div className="font-display text-base font-extrabold text-ink">
                This week
              </div>
              <div className="mt-0.5 text-[0.7rem] uppercase tracking-wide text-text-muted">
                workouts
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
