"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendAnalysis } from "@/lib/types";

interface Props { trend: TrendAnalysis; }

function formatBig(v: number): string {
  if (Math.abs(v) >= 1_000_000_000_000) return `${(v / 1_000_000_000_000).toFixed(1)}T`;
  if (Math.abs(v) >= 1_000_000_000)     return `${(v / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(v) >= 1_000_000)         return `${(v / 1_000_000).toFixed(1)}M`;
  return v.toLocaleString();
}

export default function TrendChart({ trend }: Props) {
  const years = trend.year_labels;

  const data = years.map((year, i) => ({
    year: String(year),
    Revenue:     trend.revenue.values[i]     ?? undefined,
    "Net Income": trend.net_income.values[i] ?? undefined,
    FCF:         trend.free_cash_flow.values[i] ?? undefined,
  }));

  const marginData = years.map((year, i) => ({
    year: String(year),
    "Gross Margin":     trend.margins.gross_margin_pct[i]     ?? undefined,
    "Operating Margin": trend.margins.operating_margin_pct[i] ?? undefined,
    "Net Margin":       trend.margins.net_margin_pct[i]       ?? undefined,
  }));

  return (
    <div className="space-y-8">
      {/* Revenue / NI / FCF chart */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Revenue, Net Income & FCF</h4>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={formatBig} tick={{ fontSize: 11 }} width={60} />
            <Tooltip formatter={(v: number) => formatBig(v)} />
            <Legend />
            <Line type="monotone" dataKey="Revenue"     stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="Net Income"  stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="FCF"         stroke="#8b5cf6" strokeWidth={2} dot={{ r: 4 }} strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Margin trends chart */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Tren Margin (%)</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={marginData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={45} />
            <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
            <Legend />
            <Line type="monotone" dataKey="Gross Margin"     stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="Operating Margin" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="Net Margin"       stroke="#06b6d4" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
