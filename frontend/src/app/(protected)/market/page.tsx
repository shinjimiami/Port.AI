"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  Bot,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { marketApi } from "@/lib/api";
import type { AIBrief, FearGreedData, MarketDashboard } from "@/lib/types";
import { cn } from "@/lib/utils";
import TradingViewTicker from "@/components/market/TradingViewTicker";
import TradingViewChart from "@/components/market/TradingViewChart";
import TradingViewNews from "@/components/market/TradingViewNews";

const REFRESH_INTERVAL_MS = 30_000;

// ── Fear & Greed helpers ──────────────────────────────────────────────────────

function fgColor(v: number) {
  if (v <= 25) return "text-red-600";
  if (v <= 45) return "text-orange-500";
  if (v <= 55) return "text-yellow-500";
  if (v <= 75) return "text-emerald-500";
  return "text-green-600";
}
function fgBg(v: number) {
  if (v <= 25) return "bg-red-50";
  if (v <= 45) return "bg-orange-50";
  if (v <= 55) return "bg-yellow-50";
  if (v <= 75) return "bg-emerald-50";
  return "bg-green-50";
}
function fgBar(v: number) {
  if (v <= 25) return "bg-red-500";
  if (v <= 45) return "bg-orange-500";
  if (v <= 55) return "bg-yellow-400";
  if (v <= 75) return "bg-emerald-500";
  return "bg-green-500";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FearGreedCard({ data }: { data: FearGreedData }) {
  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-brand-600" />
        <h2 className="font-semibold text-gray-800">Fear &amp; Greed Index</h2>
      </div>

      <div className={cn("rounded-xl p-5 flex flex-col items-center gap-2 mb-4", fgBg(data.value))}>
        <span className={cn("text-7xl font-bold tabular-nums leading-none", fgColor(data.value))}>
          {data.value}
        </span>
        <span className={cn("text-sm font-bold uppercase tracking-widest mt-1", fgColor(data.value))}>
          {data.classification}
        </span>
        <div className="w-full bg-white/70 rounded-full h-3 mt-2">
          <div
            className={cn("h-3 rounded-full transition-all duration-700", fgBar(data.value))}
            style={{ width: `${data.value}%` }}
          />
        </div>
        <div className="flex justify-between w-full text-xs text-gray-400 px-0.5">
          <span>Extreme Fear</span>
          <span>Extreme Greed</span>
        </div>
      </div>

      {data.history.length > 0 && (
        <div className="mt-auto">
          <p className="text-xs text-gray-400 mb-2">7-day history</p>
          <div className="flex items-end gap-1 h-12">
            {data.history.map((h, i) => (
              <div
                key={i}
                title={`${h.value} — ${h.classification}`}
                className={cn("flex-1 rounded-sm opacity-80", fgBar(h.value))}
                style={{ height: `${Math.max(12, h.value)}%` }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


function AIBriefSection({
  brief,
  loading,
  onRefresh,
}: {
  brief: AIBrief | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot size={18} className="text-brand-600" />
          <h2 className="font-semibold text-gray-800">AI Market Brief</h2>
          {brief?.is_mock && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
              Demo — add Groq key for live brief
            </span>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-brand-600 disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {loading && !brief && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          Generating market analysis with AI…
        </div>
      )}

      {brief && (
        <div>
          {brief.brief.split("\n\n").map((para, i) => (
            <p key={i} className="mb-3 last:mb-0 text-sm text-gray-700 leading-relaxed">
              {para}
            </p>
          ))}
          <p className="text-xs text-gray-400 mt-4 pt-3 border-t border-gray-100">
            Generated {brief.generated_at} · {brief.model !== "mock" ? `Model: ${brief.model}` : "Mock data"}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MarketPage() {
  const [dashboard, setDashboard] = useState<MarketDashboard | null>(null);
  const [aiBrief, setAiBrief] = useState<AIBrief | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [loadingBrief, setLoadingBrief] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await marketApi.dashboard();
      setDashboard(data);
      setLastUpdated(new Date());
      setError(null);
    } catch {
      setError("Failed to load market data. Retrying…");
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

  const fetchBrief = useCallback(async () => {
    setLoadingBrief(true);
    try {
      const data = await marketApi.aiBrief();
      setAiBrief(data);
    } catch {
      // non-fatal
    } finally {
      setLoadingBrief(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchBrief();
    timerRef.current = setInterval(fetchDashboard, REFRESH_INTERVAL_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [fetchDashboard]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Market Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Real-time data · auto-refresh every 30 seconds
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-gray-400">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={() => { fetchDashboard(); fetchBrief(); }}
            disabled={loadingDashboard}
            className="btn-secondary flex items-center gap-1.5 text-sm"
          >
            <RefreshCw size={14} className={loadingDashboard ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* ── TradingView Ticker Tape — live scrolling prices ── */}
      <TradingViewTicker />

      {/* ── TradingView Advanced Chart ── */}
      <TradingViewChart />

      {/* ── Fear & Greed + News ── */}
      {loadingDashboard && !dashboard && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[0, 1].map((i) => (
            <div key={i} className={cn("card animate-pulse", i === 1 && "lg:col-span-2")}>
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="h-32 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      )}

      {dashboard && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <FearGreedCard data={dashboard.fear_greed} />
          </div>
          <div className="lg:col-span-2">
            <TradingViewNews />
          </div>
        </div>
      )}

      {/* ── AI Market Brief ── */}
      <AIBriefSection brief={aiBrief} loading={loadingBrief} onRefresh={fetchBrief} />
    </div>
  );
}
