"use client";

import type { FundamentalScoreBreakdown } from "@/lib/types";

const CATEGORIES = [
  { key: "fundamental_health",  label: "Fundamental Health",  max: 25, color: "bg-blue-500" },
  { key: "growth_quality",      label: "Growth Quality",      max: 30, color: "bg-emerald-500" },
  { key: "earnings_integrity",  label: "Earnings Integrity",  max: 20, color: "bg-violet-500" },
  { key: "valuation",           label: "Valuation",           max: 15, color: "bg-amber-500" },
  { key: "business_momentum",   label: "Business Momentum",   max: 10, color: "bg-rose-500" },
] as const;

interface Props { breakdown: FundamentalScoreBreakdown; }

export default function ScoreBreakdown({ breakdown }: Props) {
  return (
    <div className="space-y-3">
      {CATEGORIES.map(({ key, label, max, color }) => {
        const score = breakdown[key] ?? 0;
        const pct   = Math.round((score / max) * 100);
        return (
          <div key={key}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">{label}</span>
              <span className="font-semibold text-gray-900">{score.toFixed(1)} / {max}</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${color}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
