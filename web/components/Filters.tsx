"use client";

import { useEffect, useRef } from "react";

/**
 * The filter controls, shared by the review table and the queue.
 *
 * Two shapes only.
 *
 * Seg is a segmented control rather than a dropdown. Every option is worth
 * seeing - "how many rows need attention" is itself information, and a select
 * hides it behind a click. Each option carries its own count, so the reviewer
 * knows what pressing it will cost before pressing it, and an option that would
 * show nothing says so instead of being a dead end.
 *
 * Find is a search box that is honest about being local: it filters what is
 * already on screen and never refetches, so it can be instant and can be wrong
 * about nothing.
 */

export type SegOption<T extends string> = {
  value: T;
  label: string;
  /** Rows this option would leave visible. Shown beside the label. */
  count?: number;
};

export function Seg<T extends string>({
  label, value, options, onChange,
}: {
  label: string;
  value: T;
  options: SegOption<T>[];
  onChange: (v: T) => void;
}) {
  return (
    <>
      <span className="lbl" id={`seg-${label}`}>{label}</span>
      <div className="seg" role="group" aria-labelledby={`seg-${label}`}>
        {options.map((o) => (
          <button
            key={o.value}
            aria-pressed={value === o.value}
            onClick={() => onChange(o.value)}
            // An option that would empty the table is still shown - hiding it
            // would make the zero invisible, and the zero is the finding.
            title={o.count === 0 ? `No rows match ${o.label}` : undefined}
          >
            {o.label}
            {o.count !== undefined && <span className="n">{o.count}</span>}
          </button>
        ))}
      </div>
    </>
  );
}

export function Find({
  value, onChange, placeholder = "Find…", hint,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);

  // "/" focuses the box, the convention every search field on the web uses, so
  // a reviewer working a long report never has to reach for the mouse. Escape
  // clears and releases it.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      const typing = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA"
                            || el.isContentEditable);
      if (e.key === "/" && !typing) {
        e.preventDefault();
        ref.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <input
      ref={ref}
      className="find"
      type="search"
      value={value}
      placeholder={placeholder}
      aria-label={hint ?? placeholder}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          onChange("");
          (e.target as HTMLInputElement).blur();
        }
      }}
    />
  );
}

/**
 * What the filters are hiding.
 *
 * A shorter table is only safe if it says how much it is not showing. Without
 * this line a reviewer reads twenty rows, sees no problems, and signs off on a
 * document with forty - the filter having quietly removed the twenty that
 * needed them. It is a live region so a screen reader is told the count changed
 * rather than discovering it by re-reading the table.
 */
export function HiddenNote({ hidden, onClear }: { hidden: number; onClear: () => void }) {
  if (hidden <= 0) return null;
  return (
    <div className="hidden-note" role="status">
      <span>
        {hidden} row{hidden === 1 ? "" : "s"} hidden by the filters above.
      </span>
      <button onClick={onClear}>Show everything</button>
    </div>
  );
}
