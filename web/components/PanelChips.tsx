"use client";

/**
 * Panel coverage, as chips you can press.
 *
 * A lab report arrives as panels - CHOLESTEROL PROFILE, URINE ROUTINE - and each
 * panel has a template saying which analytes belong to it. The chip says how
 * much of that template this page actually gave us.
 *
 * WHAT THE FRACTION COUNTS
 *     An analyte lands in one of five buckets. `found` is read with a certain
 *     mapping; `confirm` is read with a mapping we are guessing at; `no_value`
 *     is printed but we failed to read its number; `missing` is a core test not
 *     on the page; `absent` is an optional test the lab did not run.
 *
 *     The fraction is READ over TOTAL - how many of the panel's tests came back
 *     with a value, out of every test the panel contains. One meaning, used by
 *     the chip, the legend and the ordered-tests drawer alike.
 *
 *     It was `accounted` over `expected` - read plus the optional tests nobody
 *     ran - which made a panel read 7/7 while the legend beneath it counted
 *     three read. Both were defensible and together they were unreadable. A
 *     number on screen has to mean one thing.
 *
 *     What that costs: a panel whose optional half the lab never runs reads low,
 *     and that is the honest reading. Where the optional ones went is in the
 *     legend and in the table, named.
 *
 *     (was: everything with nothing
 *     outstanding on it, over every member of the template. `absent` counts
 *     towards the top, because an optional test nobody ran is not a gap - it is
 *     routine, and a panel that is complete apart from two unrun ratios should
 *     be able to read 8/8 rather than sitting permanently short.
 *
 *     The denominator is every member, core and optional. That is a property of
 *     the template, so one panel reads the same denominator on every document,
 *     and it is the same number the results table counts. Three numbers for one
 *     panel on one screen - chip 4/7, table All 8, legend 15 over buckets
 *     summing to 21 - is what this shape replaced.
 *
 *     All five buckets sum to the denominator, so the arithmetic is checkable
 *     by the person reading it. That property is the point of the breakdown
 *     underneath.
 */

export type PanelCoverage = {
  panel_code: string;
  panel_name: string;
  /** certain mapping */
  found: number;
  /** read, mapping is a guess */
  confirm?: number;
  /** printed, no value came out of the row */
  no_value?: number;
  /** core, not on the page */
  missing?: number;
  /** optional, not run - routine, not a hole */
  absent?: number;
  /** found + confirm */
  read?: number;
  /** read + absent: everything with nothing outstanding on it */
  accounted?: number;
  /** every member of the template, core and optional */
  expected: number;
};

/** Older payloads carry only found/expected. Fill the rest in rather than
 *  rendering NaN, and never invent a bucket we were not told about. */
function counts(p: PanelCoverage) {
  const found = p.found ?? 0;
  const confirm = p.confirm ?? 0;
  const read = p.read ?? found + confirm;
  const no_value = p.no_value ?? 0;
  const missing = p.missing ?? 0;
  const absent = p.absent ?? Math.max(0, p.expected - read - no_value - missing);
  const accounted = p.accounted ?? read + absent;
  return { found, confirm, read, accounted, no_value, missing, absent,
           expected: p.expected };
}

/** A panel is only green when nothing is outstanding. Amber the moment a core
 *  test is missing or a mapping is unconfirmed - both want a human. Red when
 *  the page gave us nothing at all, which is a different kind of problem. */
function grade(c: ReturnType<typeof counts>): "full" | "part" | "none" {
  if (c.read === 0) return "none";
  if (c.confirm === 0 && c.missing === 0 && c.no_value === 0) return "full";
  return "part";
}

function describe(name: string, c: ReturnType<typeof counts>): string {
  const bits = [
    `${c.found} read`,
    c.confirm ? `${c.confirm} awaiting confirmation` : "",
    c.no_value ? `${c.no_value} printed with no value we could read` : "",
    c.missing ? `${c.missing} not on the page` : "",
    c.absent ? `${c.absent} optional, not run` : "",
  ].filter(Boolean);
  return `${name}: ${c.expected} expected — ${bits.join(", ")}`;
}

export function PanelChips({
  panels, active, onPick,
}: {
  panels: PanelCoverage[];
  /** panel_code currently filtered to, or null for all */
  active: string | null;
  onPick: (code: string | null) => void;
}) {
  if (panels.length === 0) return null;

  return (
    <div className="pchips" role="group"
         aria-label="Panel coverage. Press one to show only that panel.">
      {panels.map((p) => {
        const c = counts(p);
        const g = grade(c);
        const pressed = active === p.panel_code;
        const pc = (n: number) => (c.expected > 0 ? (n / c.expected) * 100 : 0);
        return (
          <button
            key={p.panel_code}
            className={`pchip ${g}`}
            // The bar is the fraction, so it fills on the same number the
            // digits show. It used to fill on `found` while the digits showed
            // `read`, which put two answers on one chip.
            style={{ ["--fill" as string]: `${pc(c.read)}%` }}
            aria-pressed={pressed}
            onClick={() => onPick(pressed ? null : p.panel_code)}
            title={describe(p.panel_name, c)}
          >
            <span className="nm">{p.panel_name}</span>
            <span className="frac">
              {c.read}/{c.expected}
            </span>
            {/* A screen reader has neither the colour nor the bar, so it gets
                the whole accounting rather than a fraction it cannot place. */}
            <span className="sr-only">{describe("", c)}</span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * The same accounting in words, once, under the chips.
 *
 * The fraction says how much of the template we got. This says where the rest
 * went - and it is the line that makes "5 + 3 + 2 + 1 = 11" visible instead of
 * leaving a reviewer to work out why eleven expected produced ten rows.
 */
export function CoverageLegend(
  { panels, rows }: { panels: PanelCoverage[]; rows?: number },
) {
  if (panels.length === 0) return null;
  const t = panels.map(counts).reduce((a, c) => ({
    found: a.found + c.found,
    confirm: a.confirm + c.confirm,
    no_value: a.no_value + c.no_value,
    missing: a.missing + c.missing,
    absent: a.absent + c.absent,
    expected: a.expected + c.expected,
  }), { found: 0, confirm: 0, no_value: 0, missing: 0, absent: 0, expected: 0 });

  // "read" has to be the SAME number the chips divide by expected, or the line
  // under them contradicts them: the chip counted found + confirm, the legend
  // labelled found alone "read", and a panel reading 8/13 sat above the words
  // "3 read". One word, two meanings, both on screen at once.
  //
  // So read is found + confirm here too, and how many of those still need their
  // mapping confirmed is said as a qualifier rather than as a rival total.
  const parts: { n: number; label: string; cls: string; why: string }[] = [
    { n: t.found + t.confirm, label: "read", cls: "cv-ok",
      why: "a value was read off the page for this test" },
    { n: t.confirm, label: "of those, mapping to confirm", cls: "cv-confirm",
      why: "the value was read; only the analyte it maps onto is still a guess" },
    { n: t.no_value, label: "no value", cls: "cv-doubt",
      why: "the test is printed but no value came out of its row — our failure, not the lab's" },
    { n: t.missing, label: "not on the page", cls: "cv-doubt",
      why: "a core test of this panel that the document does not contain" },
    { n: t.absent, label: "not run", cls: "cv-faint",
      why: "optional, and the lab did not run it — listed in the table as not present" },
  ].filter((p) => p.n > 0);

  // `rows` is what the table actually lists, which is not always `expected`:
  // a row the page printed that no template mentions is real content and is
  // shown, but it is not a member of any panel. Printing `expected` twice -
  // once as "expected" and once as "rows below" - stated a row count that
  // disagreed with the buckets beside it and with the table underneath.
  const below = rows ?? t.expected;
  return (
    <p className="cov-legend">
      <b>{t.expected}</b> expected across {panels.length} panel
      {panels.length === 1 ? "" : "s"}, and <b>{below}</b> row
      {below === 1 ? "" : "s"} below:{" "}
      {parts.map((p, i) => (
        <span key={p.label}>
          {i > 0 && " · "}
          <span className={`cv ${p.cls}`} title={p.why}>
            <b>{p.n}</b> {p.label}
          </span>
        </span>
      ))}
    </p>
  );
}
