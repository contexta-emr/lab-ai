"use client";

import { useRef } from "react";

/**
 * One editable cell.
 *
 * contentEditable rather than an <input> so the table keeps its own column
 * widths - a grid of inputs stops looking like the document it is mirroring.
 *
 * It saves on blur, not on every keystroke: a PATCH per character would be
 * a request per character, and undo inside the cell would fight the server.
 * Escape restores what was there and gives up, which is what Escape means
 * everywhere else.
 */
export function Cell({
  value, onSave, className, placeholder,
}: {
  value: string | null;
  onSave: (next: string) => void;
  className?: string;
  placeholder?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const initial = value ?? "";

  return (
    <div
      ref={ref}
      className={`cell ${className ?? ""}`}
      contentEditable
      suppressContentEditableWarning
      role="textbox"
      tabIndex={0}
      data-placeholder={placeholder}
      onBlur={(e) => {
        const next = (e.currentTarget.textContent ?? "").trim();
        if (next !== initial) onSave(next);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") { e.preventDefault(); e.currentTarget.blur(); }
        if (e.key === "Escape") {
          e.preventDefault();
          e.currentTarget.textContent = initial;
          e.currentTarget.blur();
        }
      }}
    >
      {initial}
    </div>
  );
}
