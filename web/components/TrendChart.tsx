"use client";

import { useState } from "react";
import type { Trend, TrendPoint } from "@/lib/api";

type Dated = TrendPoint & { collected_at: string };

const FLAG_WORD: Record<string, string> = {
  H: "High",
  L: "Low",
  HH: "Very high",
  LL: "Very low",
  A: "Abnormal",
};

/**
 * A five-year trend, drawn as inline SVG.
 *
 * No charting library: one line, a reference band behind it and a tooltip,
 * which is less code than a dependency. Three decisions worth stating:
 *
 * - The x axis is spaced by ACTUAL DATE, not by index. Readings three months
 *   apart and three years apart must not look the same; the gap is clinical
 *   information.
 * - Every point is drawn. A chart that quietly drops a reading is worse than
 *   no chart.
 * - The curve is monotone (Fritsch-Carlson). It bends smoothly but never
 *   overshoots a reading, so it cannot draw a peak or a trough that was never
 *   measured.
 */
export function TrendChart({ trend }: { trend: Trend }) {
  const [hover, setHover] = useState<number | null>(null);
  const readable = trend.points.filter((p) => p.value_numeric !== null);
  // A reading whose date could not be read has no place on a date axis. It
  // used to reach new Date(null) - 1 January 1970 - and crush the real readings
  // into a corner (review B3). It is left off and SAID so below, and the rest
  // are sorted by date so the line can never double back.
  const points = readable
    .filter((p): p is Dated => p.collected_at !== null)
    .sort((a, b) => Date.parse(a.collected_at) - Date.parse(b.collected_at));
  const undated = readable.length - points.length;
  const note =
    undated > 0 ? (
      <p className="faint" style={{ fontSize: 12, margin: "6px 0 0" }}>
        {undated} reading{undated === 1 ? " has" : "s have"} no date and{" "}
        {undated === 1 ? "is" : "are"} not plotted. {undated === 1 ? "It is" : "They are"} in the
        table below.
      </p>
    ) : null;
  if (points.length === 0) return note;

  const W = 720;
  const H = 260;
  const PAD = { top: 18, right: 20, bottom: 30, left: 52 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const times = points.map((p) => new Date(p.collected_at).getTime());
  const values = points.map((p) => p.value_numeric as number);
  const refLow = points.find((p) => p.ref_low !== null)?.ref_low ?? null;
  const refHigh = points.find((p) => p.ref_high !== null)?.ref_high ?? null;

  // The band must sit inside the visible range, or an all-normal series draws
  // a band nobody can see.
  const lo = Math.min(...values, refLow ?? Infinity);
  const hi = Math.max(...values, refHigh ?? -Infinity);
  const span = hi - lo || Math.abs(hi) || 1;
  // Round numbers on the axis (4, 5, 6 - not 4.61, 5.70), with a little room
  // so no reading sits on the edge.
  const { min: yMin, max: yMax, step } = niceScale(lo - span * 0.08, hi + span * 0.08);
  const tMin = Math.min(...times);
  const tMax = Math.max(...times);
  const tSpan = tMax - tMin || 1;

  // A single reading sits in the middle rather than on the left edge.
  const x = (t: number) =>
    tMax === tMin ? PAD.left + plotW / 2 : PAD.left + ((t - tMin) / tSpan) * plotW;
  const y = (v: number) => PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
  const xs = times.map(x);
  const ys = values.map(y);

  const line = smoothPath(xs, ys);
  const bottom = PAD.top + plotH;
  const area = `${line} L ${xs[xs.length - 1].toFixed(1)} ${bottom} L ${xs[0].toFixed(1)} ${bottom} Z`;

  const yTicks = Array.from(
    { length: Math.round((yMax - yMin) / step) + 1 },
    (_, i) => yMin + step * i,
  );
  const yearTicks: number[] = [];
  for (let yr = new Date(tMin).getFullYear(); yr <= new Date(tMax).getFullYear(); yr++) {
    const t = new Date(yr, 0, 1).getTime();
    if (t >= tMin && t <= tMax) yearTicks.push(t);
  }

  const abnormal = (p: TrendPoint) => Boolean(p.flag && FLAG_WORD[p.flag]);
  const shown = hover === null ? null : points[hover];

  return (
    <>
      <div className="trend">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: "100%", height: "auto", display: "block" }}
          role="img"
          aria-label={`${trend.analyte_name ?? trend.analyte_code} over time, ${points.length} readings`}
          onMouseLeave={() => setHover(null)}
        >
          <defs>
            <linearGradient id="trend-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#00878a" stopOpacity="0.13" />
              <stop offset="75%" stopColor="#00878a" stopOpacity="0" />
            </linearGradient>
          </defs>

          {refLow !== null && refHigh !== null && (
            <>
              <rect
                x={PAD.left}
                y={y(refHigh)}
                width={plotW}
                height={Math.max(y(refLow) - y(refHigh), 1)}
                fill="#e7f5f0"
                rx={4}
              />
              {/* Inside the band's top-left corner, where no reading can sit on
                  it; above the band when the band is too thin to hold it. */}
              <text
                x={PAD.left + 8}
                y={y(refLow) - y(refHigh) > 18 ? y(refHigh) + 14 : y(refHigh) - 5}
                fontSize="10.5"
                fontWeight={500}
                fill="#1e7a4b"
              >
                normal {refLow}–{refHigh}
              </text>
            </>
          )}

          {yTicks.map((v, i) => (
            <g key={i}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(v)}
                y2={y(v)}
                stroke="#eef1f2"
                strokeWidth={1}
              />
              <text x={PAD.left - 8} y={y(v) + 3.5} textAnchor="end" fontSize="10.5" fill="#8a9294">
                {formatTick(v)}
              </text>
            </g>
          ))}

          {yearTicks.map((t) => (
            <text key={t} x={x(t)} y={H - 9} textAnchor="middle" fontSize="10.5" fill="#8a9294">
              {new Date(t).getFullYear()}
            </text>
          ))}

          <path className="trend-area" d={area} fill="url(#trend-fill)" />
          <path
            className="trend-line"
            d={line}
            pathLength={1}
            fill="none"
            stroke="#00878a"
            strokeWidth={2.4}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {hover !== null && (
            <line
              x1={xs[hover]}
              x2={xs[hover]}
              y1={PAD.top}
              y2={bottom}
              stroke="#00878a"
              strokeOpacity={0.25}
              strokeDasharray="3 3"
            />
          )}

          {points.map((p, i) => (
            <g key={i}>
              <circle
                cx={xs[i]}
                cy={ys[i]}
                r={hover === i ? 6 : abnormal(p) ? 4.8 : 3.6}
                fill={abnormal(p) ? "#fb7d54" : "#00878a"}
                stroke="#fff"
                strokeWidth={1.8}
              />
              {/* A wider, invisible target, so a point is easy to hit with a mouse or a finger. */}
              <circle
                cx={xs[i]}
                cy={ys[i]}
                r={14}
                fill="transparent"
                tabIndex={0}
                aria-label={`${new Date(p.collected_at).toLocaleDateString("en-IN")}: ${p.value_text}${p.unit ? ` ${p.unit}` : ""}`}
                onMouseEnter={() => setHover(i)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                onClick={() => setHover(i)}
              />
            </g>
          ))}
        </svg>

        {shown && hover !== null && (
          <div
            className="trend-tip"
            style={{ left: `${(xs[hover] / W) * 100}%`, top: `${(ys[hover] / H) * 100}%` }}
          >
            <strong>
              {shown.value_text}
              {shown.unit ? ` ${shown.unit}` : ""}
            </strong>
            {shown.flag && FLAG_WORD[shown.flag] ? (
              <span className="flag"> · {FLAG_WORD[shown.flag]}</span>
            ) : null}
            <div>
              {new Date(shown.collected_at).toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </div>
            {shown.lab_name ? <div className="tip-lab">{shown.lab_name}</div> : null}
          </div>
        )}
      </div>
      {note}
    </>
  );
}

/** A monotone cubic through the points (Fritsch-Carlson): smooth, never overshooting. */
function smoothPath(xs: number[], ys: number[]): string {
  const n = xs.length;
  if (n === 1) return `M ${xs[0].toFixed(1)} ${ys[0].toFixed(1)}`;
  const dx: number[] = [];
  const slope: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    dx[i] = xs[i + 1] - xs[i] || 1e-6; // two readings on one day
    slope[i] = (ys[i + 1] - ys[i]) / dx[i];
  }
  const m: number[] = [slope[0]];
  for (let i = 1; i < n - 1; i++) {
    m[i] = slope[i - 1] * slope[i] <= 0 ? 0 : (slope[i - 1] + slope[i]) / 2;
  }
  m[n - 1] = slope[n - 2];
  for (let i = 0; i < n - 1; i++) {
    if (slope[i] === 0) {
      m[i] = 0;
      m[i + 1] = 0;
      continue;
    }
    const a = m[i] / slope[i];
    const b = m[i + 1] / slope[i];
    const h = a * a + b * b;
    if (h > 9) {
      const t = 3 / Math.sqrt(h);
      m[i] = t * a * slope[i];
      m[i + 1] = t * b * slope[i];
    }
  }
  let d = `M ${xs[0].toFixed(1)} ${ys[0].toFixed(1)}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3;
    d +=
      ` C ${(xs[i] + h).toFixed(1)} ${(ys[i] + m[i] * h).toFixed(1)},` +
      ` ${(xs[i + 1] - h).toFixed(1)} ${(ys[i + 1] - m[i + 1] * h).toFixed(1)},` +
      ` ${xs[i + 1].toFixed(1)} ${ys[i + 1].toFixed(1)}`;
  }
  return d;
}

/** Round bounds and a 1, 2, 2.5 or 5 step, about four of them across the range. */
function niceScale(lo: number, hi: number): { min: number; max: number; step: number } {
  const raw = (hi - lo || Math.abs(hi) || 1) / 4;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? raw;
  return { min: Math.floor(lo / step) * step, max: Math.ceil(hi / step) * step, step };
}

function formatTick(v: number): string {
  // toFixed first, so 0.30000000000000004 prints as 0.3.
  return Number(v.toFixed(6)).toLocaleString("en-IN", { maximumFractionDigits: 3 });
}
