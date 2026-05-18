"use client";

import { cn } from "@/lib/utils";
import type { RatioYear } from "@/lib/types";

interface Row {
  label: string;
  section: keyof Omit<RatioYear, "year">;
  field: string;
  format: (v: number) => string;
  good?: (v: number) => boolean;
}

const ROWS: Row[] = [
  // Profitability
  { label: "Gross Margin",     section: "profitability", field: "gross_margin_pct",     format: (v) => `${v.toFixed(1)}%`, good: (v) => v > 30 },
  { label: "Operating Margin", section: "profitability", field: "operating_margin_pct", format: (v) => `${v.toFixed(1)}%`, good: (v) => v > 10 },
  { label: "Net Margin",       section: "profitability", field: "net_margin_pct",       format: (v) => `${v.toFixed(1)}%`, good: (v) => v > 8  },
  { label: "ROE",              section: "profitability", field: "roe_pct",              format: (v) => `${v.toFixed(1)}%`, good: (v) => v > 15 },
  { label: "ROA",              section: "profitability", field: "roa_pct",              format: (v) => `${v.toFixed(1)}%`, good: (v) => v > 5  },
  // Liquidity
  { label: "Current Ratio",   section: "liquidity", field: "current_ratio", format: (v) => v.toFixed(2), good: (v) => v > 1.5 },
  { label: "Quick Ratio",     section: "liquidity", field: "quick_ratio",   format: (v) => v.toFixed(2), good: (v) => v > 1.0 },
  // Solvency
  { label: "DER",              section: "solvency", field: "der",              format: (v) => v.toFixed(2), good: (v) => v < 1.5 },
  { label: "Interest Coverage",section: "solvency", field: "interest_coverage", format: (v) => `${v.toFixed(1)}x`, good: (v) => v > 3  },
  // Cash Quality
  { label: "Cash Conversion",  section: "cash_quality", field: "cash_conversion_ratio", format: (v) => v.toFixed(2), good: (v) => v > 0.8 },
  { label: "FCF Margin",       section: "cash_quality", field: "fcf_margin_pct",        format: (v) => `${v.toFixed(1)}%`, good: (v) => v > 5 },
];

const SECTION_HEADERS: { label: string; before: string }[] = [
  { label: "Profitabilitas", before: "gross_margin_pct" },
  { label: "Likuiditas",     before: "current_ratio"    },
  { label: "Solvabilitas",   before: "der"              },
  { label: "Kualitas Kas",   before: "cash_conversion_ratio" },
];

interface Props { years: RatioYear[]; }

export default function RatioTable({ years }: Props) {
  const sorted = [...years].sort((a, b) => a.year - b.year);

  function getValue(row: Row, y: RatioYear): number | null {
    const section = y[row.section] as Record<string, number | null>;
    return section?.[row.field] ?? null;
  }

  function getSectionHeader(field: string) {
    return SECTION_HEADERS.find((h) => h.before === field);
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 pr-4 text-gray-500 font-medium">Rasio</th>
            {sorted.map((y) => (
              <th key={y.year} className="text-right py-2 px-3 text-gray-700 font-semibold">
                {y.year}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const header = getSectionHeader(row.field);
            return (
              <>
                {header && (
                  <tr key={`header-${row.field}`}>
                    <td colSpan={sorted.length + 1} className="pt-4 pb-1 text-xs font-bold text-gray-400 uppercase tracking-wider">
                      {header.label}
                    </td>
                  </tr>
                )}
                <tr key={row.field} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-2 pr-4 text-gray-600">{row.label}</td>
                  {sorted.map((y) => {
                    const val = getValue(row, y);
                    const isGood = val !== null && row.good ? row.good(val) : null;
                    return (
                      <td key={y.year} className={cn(
                        "text-right py-2 px-3 font-medium tabular-nums",
                        isGood === true  && "text-emerald-600",
                        isGood === false && "text-red-600",
                        isGood === null  && "text-gray-400",
                      )}>
                        {val !== null ? row.format(val) : "—"}
                      </td>
                    );
                  })}
                </tr>
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
