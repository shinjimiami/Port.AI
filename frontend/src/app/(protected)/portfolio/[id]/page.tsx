"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, Bookmark, Download, Info } from "lucide-react";
import { portfolioApi } from "@/lib/api";
import type { Portfolio } from "@/lib/types";
import { cn, formatCurrency, formatDate, RISK_COLORS, STATUS_COLORS } from "@/lib/utils";
import AllocationPieChart from "@/components/portfolio/AllocationPieChart";
import AssetCard from "@/components/portfolio/AssetCard";
import RiskMetricsCard from "@/components/portfolio/RiskMetricsCard";
import RebalancingCard from "@/components/portfolio/RebalancingCard";
import ProgressTracker from "@/components/portfolio/ProgressTracker";

export default function PortfolioPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const portfolioId = parseInt(id);

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    portfolioApi
      .get(portfolioId)
      .then(setPortfolio)
      .catch(() => router.push("/dashboard"))
      .finally(() => setLoading(false));
  }, [portfolioId, router]);

  async function handleSave() {
    await portfolioApi.save(portfolioId);
    setSaved(true);
  }

  async function handleDownloadPdf() {
    setDownloading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("portai_token");
      const res = await fetch(`${apiUrl}/api/v1/portfolio/${portfolioId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `portai_report_${portfolioId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Could not download PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!portfolio) return null;

  // Still processing — show live tracker
  if (portfolio.status === "processing" || portfolio.status === "pending") {
    return (
      <div>
        <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
          <ArrowLeft size={16} /> Back
        </button>
        <ProgressTracker portfolioId={portfolioId} />
      </div>
    );
  }

  const report = portfolio.report;

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3"
          >
            <ArrowLeft size={16} /> Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio Report</h1>
          <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
            <span>{formatDate(portfolio.created_at)}</span>
            <span>·</span>
            <span>{portfolio.horizon}</span>
            <span>·</span>
            <span>{formatCurrency(portfolio.budget, portfolio.currency)}</span>
            {portfolio.risk_tolerance && (
              <>
                <span>·</span>
                <span
                  className={cn(
                    "px-2 py-0.5 rounded-full text-xs font-medium",
                    RISK_COLORS[portfolio.risk_tolerance]
                  )}
                >
                  {portfolio.risk_tolerance}
                </span>
              </>
            )}
            <span
              className={cn(
                "px-2 py-0.5 rounded-full text-xs font-medium",
                STATUS_COLORS[portfolio.status]
              )}
            >
              {portfolio.status}
            </span>
          </div>
        </div>

        {portfolio.status === "completed" && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={downloading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300
                         text-gray-700 hover:bg-gray-50 text-sm font-medium transition-colors
                         disabled:opacity-50"
            >
              <Download size={16} />
              {downloading ? "Generating…" : "PDF"}
            </button>
            <button
              onClick={handleSave}
              disabled={saved}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors",
                saved
                  ? "bg-green-50 border-green-200 text-green-700"
                  : "border-gray-300 text-gray-700 hover:bg-gray-50"
              )}
            >
              <Bookmark size={16} />
              {saved ? "Saved" : "Save"}
            </button>
          </div>
        )}
      </div>

      {/* Failed state */}
      {portfolio.status === "failed" && (
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center gap-2 text-red-700">
            <AlertTriangle size={20} />
            <p className="font-medium">Generation failed</p>
          </div>
          <p className="text-red-600 text-sm mt-1">Please try generating a new portfolio.</p>
        </div>
      )}

      {report && (
        <>
          {/* Summary */}
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-2">Executive Summary</h2>
            <p className="text-gray-700 text-sm leading-relaxed">{report.summary}</p>
          </div>

          {/* Allocation chart + risk metrics side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AllocationPieChart
              allocation={report.allocation}
              currency={report.currency}
            />
            <div className="space-y-6">
              <RiskMetricsCard metrics={report.risk_metrics} />
              <RebalancingCard rebalancing={report.rebalancing} />
            </div>
          </div>

          {/* Asset grid */}
          <div>
            <h2 className="font-semibold text-gray-900 mb-4">
              Selected Assets ({report.assets.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {report.assets.map((asset) => (
                <AssetCard key={asset.ticker} asset={asset} currency={report.currency} />
              ))}
            </div>
          </div>

          {/* Market context */}
          {report.market_context && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Info size={18} className="text-brand-500" />
                <h2 className="font-semibold text-gray-900">Market Context</h2>
              </div>
              <p className="text-gray-700 text-sm leading-relaxed">{report.market_context}</p>
            </div>
          )}

          {/* Warnings */}
          {report.warnings.length > 0 && (
            <div className="card bg-amber-50 border-amber-100">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={18} className="text-amber-600" />
                <h2 className="font-semibold text-amber-800">Warnings</h2>
              </div>
              <ul className="space-y-2">
                {report.warnings.map((w, i) => (
                  <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                    <span className="font-bold mt-0.5">·</span> {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Disclaimer */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl px-6 py-4">
            <p className="text-xs text-gray-500 leading-relaxed">{report.disclaimer}</p>
          </div>
        </>
      )}
    </div>
  );
}
