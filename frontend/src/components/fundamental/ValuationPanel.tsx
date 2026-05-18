"use client";

import type { ValuationResult } from "@/lib/types";

const ZONE_COLORS: Record<string, string> = {
  DEEPLY_UNDERVALUED:       "text-emerald-700 bg-emerald-50 border-emerald-200",
  UNDERVALUED:              "text-green-700   bg-green-50   border-green-200",
  FAIRLY_VALUED:            "text-yellow-700  bg-yellow-50  border-yellow-200",
  OVERVALUED:               "text-orange-700  bg-orange-50  border-orange-200",
  SIGNIFICANTLY_OVERVALUED: "text-red-700     bg-red-50     border-red-200",
};

interface Props { valuation: ValuationResult; }

function Row({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex justify-between py-2 border-b border-gray-50 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-900">{value ?? "—"}</span>
    </div>
  );
}

export default function ValuationPanel({ valuation }: Props) {
  if (valuation.skipped) {
    return (
      <p className="text-sm text-gray-400 italic">
        Valuasi tidak tersedia — harga saham saat ini tidak dimasukkan.
      </p>
    );
  }

  const { dcf, relative, zone, current_price, is_usd_report } = valuation;
  const zoneStyle = ZONE_COLORS[zone?.key ?? ""] ?? "text-gray-700 bg-gray-50 border-gray-200";

  return (
    <div className="space-y-4">
      {is_usd_report && (
        <div className="text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2">
          Laporan keuangan dalam USD — estimasi nilai wajar sudah dikonversi ke IDR (kurs ≈ 16.000).
        </div>
      )}
      {zone && (
        <div className={`border rounded-lg px-4 py-3 ${zoneStyle}`}>
          <p className="font-bold text-base">{zone.label}</p>
          <p className="text-sm mt-0.5">
            Harga saat ini {(zone.price_to_intrinsic * 100).toFixed(0)}% dari estimasi nilai wajar
          </p>
        </div>
      )}

      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">DCF Valuation</p>
        <Row label="Harga Saat Ini"        value={current_price ? `${current_price.toLocaleString()}` : null} />
        <Row label="Estimasi Nilai Wajar"  value={dcf.intrinsic_value_per_share ? dcf.intrinsic_value_per_share.toLocaleString() : null} />
        <Row label="Asumsi Growth Rate"    value={`${dcf.growth_rate_pct}%`} />
        <Row label="WACC"                  value={`${dcf.wacc_pct}%`} />
        <Row label="Terminal Growth"       value={`${dcf.terminal_growth_pct}%`} />
      </div>

      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Relative Valuation</p>
        <Row label="P/E (current)"  value={relative.pe_current  ? `${relative.pe_current}x`  : null} />
        <Row label="P/BV (current)" value={relative.pbv_current ? `${relative.pbv_current}x` : null} />
        <Row label="EPS (latest)"   value={relative.eps_latest  ? relative.eps_latest.toLocaleString() : null} />
      </div>
    </div>
  );
}
