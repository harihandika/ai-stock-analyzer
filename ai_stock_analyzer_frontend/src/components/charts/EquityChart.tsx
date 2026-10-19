"use client";
import { useId, useState } from "react";

export function EquityChart({
  points,
}: {
  points: { date: string; equity: number }[];
}) {
  const id = useId();
  const [index, setIndex] = useState<number | null>(null);
  if (!points.length) return <p>Equity curve belum tersedia.</p>;
  const values = points.map((p) => p.equity),
    min = Math.min(...values),
    max = Math.max(...values);
  const coordinates = points
    .map(
      (p, i) =>
        `${20 + (i / Math.max(1, points.length - 1)) * 560},${170 - ((p.equity - min) / Math.max(1, max - min)) * 140}`,
    )
    .join(" ");
  const selected = points[index ?? points.length - 1];
  return (
    <figure className="border border-slate-700 rounded p-4 space-y-2">
      <figcaption id={id}>
        Equity curve setelah biaya · {selected.date}:{" "}
        {selected.equity.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
      </figcaption>
      <svg
        viewBox="0 0 600 200"
        role="img"
        aria-labelledby={id}
        className="w-full"
      >
        <polyline
          points={coordinates}
          stroke="#38bdf8"
          strokeWidth="2"
          fill="none"
        />
        <text x="20" y="195" fill="#cbd5e1" fontSize="12">
          {points[0].date}
        </text>
        <text x="480" y="195" fill="#cbd5e1" fontSize="12">
          {points.at(-1)?.date}
        </text>
      </svg>
      <label className="block">
        Periksa sesi equity
        <input
          className="block w-full"
          type="range"
          min={0}
          max={points.length - 1}
          value={index ?? points.length - 1}
          onChange={(e) => setIndex(Number(e.target.value))}
        />
      </label>
    </figure>
  );
}
