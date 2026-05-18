"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AlertCircle, ArrowLeft, ExternalLink, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { fundamentalApi } from "@/lib/api";
import type { FundamentalAnalysis } from "@/lib/types";
import SignalBadge    from "@/components/fundamental/SignalBadge";
import ScoreBreakdown from "@/components/fundamental/ScoreBreakdown";
import RatioTable     from "@/components/fundamental/RatioTable";
import TrendChart     from "@/components/fundamental/TrendChart";
import RedFlagsPanel  from "@/components/fundamental/RedFlagsPanel";
import ValuationPanel from "@/components/fundamental/ValuationPanel";

export default function FundamentalReportPage() {
  const { id }  = useParams<{ id: string }>();
  const router  = useRouter();
  const [data,  setData]  = useState<FundamentalAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fundamentalApi.get(Number(id))
      .then(setData)
      .catch(() => setError("Analisis tidak ditemukan atau terjadi kesalahan."));
  }, [id]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <AlertCircle className="mx-auto mb-3 text-red-400" size={40} />
        <p className="text-gray-600">{error}</p>
        <Link href="/analyze/fundamental" className="btn-secondary mt-4 inline-block">
          Kembali
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-brand-600" size={36} />
      </div>
    );
  }

  if (data.status === "failed") {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <AlertCircle className="mx-auto mb-3 text-red-400" size={40} />
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Analisis Gagal</h2>
        <p className="text-sm text-gray-500 mb-4">{data.error_message}</p>
        <Link href="/analyze/fundamental" className="btn-primary inline-block">
          Coba Lagi
        </Link>
      </div>
    );
  }

  const signal = data.entry_signal?.signal;
  const score  = data.entry_signal?.total_score ?? 0;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-gray-700">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{data.ticker}</h1>
          <p className="text-sm text-gray-400">
            Analisis Fundamental · {new Date(data.created_at).toLocaleDateString("id-ID", { dateStyle: "long" })}
          </p>
        </div>
      </div>

      {/* Entry Signal — top hero card */}
      {signal && (
        <div className="card flex flex-col sm:flex-row items-center gap-6">
          <SignalBadge signalKey={signal.key} label={signal.label} score={score} size="lg" />
          <div className="flex-1 w-full">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Score Breakdown</p>
            {data.entry_signal?.breakdown && (
              <ScoreBreakdown breakdown={data.entry_signal.breakdown} />
            )}
          </div>
        </div>
      )}

      {/* Strengths & Risks */}
      {data.entry_signal && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="card">
            <h3 className="text-sm font-bold text-emerald-700 mb-3">✅ Kekuatan Utama</h3>
            <ul className="space-y-2">
              {data.entry_signal.key_strengths.map((s, i) => (
                <li key={i} className="text-sm text-gray-600 flex gap-2">
                  <span className="text-emerald-500 shrink-0">•</span>{s}
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h3 className="text-sm font-bold text-red-600 mb-3">⚠️ Risiko Utama</h3>
            <ul className="space-y-2">
              {data.entry_signal.key_risks.map((r, i) => (
                <li key={i} className="text-sm text-gray-600 flex gap-2">
                  <span className="text-red-400 shrink-0">•</span>{r}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Entry Zone */}
      {data.entry_signal?.entry_zone && (
        <div className="card bg-brand-50 border-brand-200">
          <h3 className="text-sm font-bold text-brand-700 mb-3">📍 Zona Entry Saham</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            {[
              { label: "Harga Saat Ini",     value: data.entry_signal.entry_zone.current_price },
              { label: "Estimasi Fair Value", value: data.entry_signal.entry_zone.intrinsic_estimate },
              { label: "Entry Menarik",       value: data.entry_signal.entry_zone.attractive_entry },
              { label: "Entry Wajar",         value: data.entry_signal.entry_zone.fair_entry },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className="text-lg font-bold text-brand-700">{value.toLocaleString("id-ID")}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            Horizon: {data.entry_signal.suggested_horizon}
          </p>
        </div>
      )}

      {/* 3-Year Trend Charts */}
      {data.trend_analysis && (
        <div className="card">
          <h2 className="text-base font-bold text-gray-800 mb-4">Tren 3 Tahun</h2>
          <TrendChart trend={data.trend_analysis} />
          {data.trend_analysis.detected_patterns.length > 0 && (
            <div className="mt-4 space-y-1">
              {data.trend_analysis.detected_patterns.map((p, i) => (
                <p key={i} className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded px-3 py-2">
                  ⚠️ {p}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Ratio Table */}
      {data.ratios?.years?.length && (
        <div className="card">
          <h2 className="text-base font-bold text-gray-800 mb-4">Tabel Rasio Keuangan</h2>
          <RatioTable years={data.ratios.years} />
        </div>
      )}

      {/* Red Flags */}
      <div className="card">
        <h2 className="text-base font-bold text-gray-800 mb-4">Red Flag & Peringatan</h2>
        <RedFlagsPanel flags={data.red_flags ?? []} />
      </div>

      {/* Valuation */}
      {data.valuation && (
        <div className="card">
          <h2 className="text-base font-bold text-gray-800 mb-4">Valuasi</h2>
          <ValuationPanel valuation={data.valuation} />
        </div>
      )}

      {/* Narrative Report */}
      {data.narrative_report && (
        <div className="card prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600">
          <ReactMarkdown>{data.narrative_report}</ReactMarkdown>
        </div>
      )}

      {/* CTA — use in portfolio generator */}
      <div className="card bg-gray-50 border-gray-200 flex flex-col sm:flex-row items-center gap-4">
        <div className="flex-1">
          <p className="font-semibold text-gray-800">Gunakan saham ini di Portfolio Generator</p>
          <p className="text-sm text-gray-500">
            Pre-fill generator dengan {data.ticker} · Score: {score.toFixed(1)}/100
          </p>
        </div>
        <Link
          href={`/generate?ticker=${data.ticker}&score=${score.toFixed(1)}`}
          className="btn-primary flex items-center gap-2 whitespace-nowrap"
        >
          Buka Generator <ExternalLink size={14} />
        </Link>
      </div>

    </div>
  );
}
