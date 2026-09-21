"use client";

import type { Trend } from "@/lib/api";

/**
 * A five-year trend, drawn as inline SVG.
 *
 * No charting library: this draws one line with a reference band behind it, and
 * a dependency would be more code than the thing it replaces.
 *
 * Two decisions worth stating. The x axis is spaced by *actual date*, not by
 * index — readings three months apart and three years apart must not look the
 * same, because the gap is clinical information. And every point is drawn: a
 * chart that quietly drops a reading is worse than no chart.
 */
export function TrendChart({ trend }: { trend: Trend }) {
  const points = trend.points.filter((p) => p.value_numeric !== null);
  if (points.length === 0) return null;

  const W = 720;
  const H = 240;
  const PAD = { top: 16, right: 18, bottom: 28, left: 52 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const times = points.map((p) => new Date(p.collected_at).getTime());
  const values = points.map((p) => p.value_numeric as number);

  const refLow = points.find((p) => p.ref_low !== null)?.ref_low ?? null;
  const refHigh = points.find((p) => p.ref_high !== null)?.ref_high ?? null;

  // The reference band has to be inside the visible range, or an all-normal
  // series draws a band nobody can see.
  const lo = Math.min(...values, refLow ?? Infinity);
  const hi = Math.max(...values, refHigh ?? -Infinity);
  const span = hi - lo || Math.abs(hi) || 1;
  const yMin = lo - span * 0.12;
  const yMax = hi + span * 0.12;

  const tMin = Math.min(...times);
  const tMax = Math.max(...times);
  const tSpan = tMax - tMin || 1;

  const x = (t: number) => PAD.left + ((t - tMin) / tSpan) * plotW;
  const y = (v: number) => PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${x(times[i]).toFixed(1)} ${y(values[i]).toFixed(1)}`)
    .join(" ");

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + ((yMax - yMin) / ticks) * i);

  const firstYear = new Date(tMin).getFullYear();
  const lastYear = new Date(tMax).getFullYear();
  const yearTicks: number[] = [];
  for (let yr = firstYear; yr <= lastYear; yr++) {
    const t = new Date(yr, 0, 1).getTime();
    if (t >= tMin && t <= tMax) yearTicks.push(t);
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: "100%", height: "auto", display: "block" }}
      role="img"
      aria-label={`${trend.analyte_name ?? trend.analyte_code} over time, ${points.length} readings`}
    >
      {refLow !== null && refHigh !== null && (
        <>
          <rect
            x={PAD.left}
            y={y(refHigh)}
            width={plotW}
            height={Math.max(y(refLow) - y(refHigh), 1)}
            fill="#e8f5ee"
          />
          <text x={W - PAD.right} y={y(refHigh) - 4} textAnchor="end" fontSize="10" fill="#1e7a4b">
            normal {refLow}–{refHigh}
          </text>
        </>
      )}

      {yTicks.map((v, i) => (
        <g key={i}>
          <line
            x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)}
            stroke="#eef1f4" strokeWidth={1}
          />
          <text x={PAD.left - 8} y={y(v) + 3.5} textAnchor="end" fontSize="10" fill="#8a97a4">
            {formatTick(v)}
          </text>
        </g>
      ))}

      {yearTicks.map((t) => (
        <text key={t} x={x(t)} y={H - 8} textAnchor="middle" fontSize="10" fill="#8a97a4">
          {new Date(t).getFullYear()}
        </text>
      ))}

      <path d={path} fill="none" stroke="#10375f" strokeWidth={1.8}
            strokeLinejoin="round" strokeLinecap="round" />

      {points.map((p, i) => {
        const abnormal = p.flag === "H" || p.flag === "L";
        return (
          <circle
            key={i}
            cx={x(times[i])}
            cy={y(values[i])}
            r={abnormal ? 4.2 : 3.2}
            fill={p.flag === "H" ? "#b3261e" : p.flag === "L" ? "#1d5fa8" : "#10375f"}
            stroke="#fff"
            strokeWidth={1.4}
          >
            <title>
              {new Date(p.collected_at).toLocaleDateString("en-IN")} — {p.value_text}
              {p.unit ? ` ${p.unit}` : ""}
              {p.flag ? ` (${p.flag})` : ""}
              {p.lab_name ? `\n${p.lab_name}` : ""}
            </title>
          </circle>
        );
      })}
    </svg>
  );
}

function formatTick(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 100000) return `${Math.round(v / 1000)}k`;
  if (abs >= 1000) return v.toFixed(0);
  if (abs >= 10) return v.toFixed(1);
  return v.toFixed(2);
}
