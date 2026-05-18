"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { portfolioApi } from "@/lib/api";
import type { AssetClass, GeneratePortfolioRequest, Horizon } from "@/lib/types";
import ProgressTracker from "@/components/portfolio/ProgressTracker";

const HORIZONS: Horizon[] = ["1 month", "3 months", "6 months", "1 year", "3 years", "5 years"];

const ASSET_CLASSES: { value: AssetClass; label: string; desc: string }[] = [
  { value: "US_STOCKS", label: "US Stocks",  desc: "S&P 500 blue chips via Alpha Vantage" },
  { value: "IDX",       label: "IDX Stocks", desc: "Indonesian blue chips via Yahoo Finance" },
  { value: "CRYPTO",    label: "Crypto",     desc: "Top 50 coins via CoinGecko" },
];

export default function GeneratePage() {
  const [form, setForm] = useState({
    budget: "",
    currency: "USD",
    horizon: "6 months" as Horizon,
    risk_tolerance: "",
    asset_classes: ["US_STOCKS"] as AssetClass[],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [generatingId, setGeneratingId] = useState<number | null>(null);

  function toggleAsset(val: AssetClass) {
    setForm((f) => ({
      ...f,
      asset_classes: f.asset_classes.includes(val)
        ? f.asset_classes.filter((a) => a !== val)
        : [...f.asset_classes, val],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!form.budget || parseFloat(form.budget) <= 0) {
      setError("Please enter a valid budget amount.");
      return;
    }
    if (form.asset_classes.length === 0) {
      setError("Select at least one asset class.");
      return;
    }

    setLoading(true);
    try {
      const payload: GeneratePortfolioRequest = {
        budget: parseFloat(form.budget),
        currency: form.currency,
        horizon: form.horizon,
        asset_classes: form.asset_classes,
        risk_tolerance: (form.risk_tolerance as GeneratePortfolioRequest["risk_tolerance"]) || null,
      };
      const portfolio = await portfolioApi.generate(payload);
      setGeneratingId(portfolio.id);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Failed to start generation. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  // Show progress tracker once generation started
  if (generatingId) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Generating Portfolio</h1>
        <p className="text-gray-500 text-sm mb-8">
          Our multi-agent AI is building your personalised report. This takes 30–90 seconds.
        </p>
        <ProgressTracker portfolioId={generatingId} />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Generate Portfolio</h1>
        <p className="text-gray-500 text-sm mt-1">
          Fill in your investment preferences and let the AI do the rest.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Budget */}
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">Investment Amount</h2>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="label">Budget</label>
              <input
                type="number"
                className="input-field"
                placeholder="e.g. 5000"
                min={1}
                value={form.budget}
                onChange={(e) => setForm((f) => ({ ...f, budget: e.target.value }))}
                required
              />
            </div>
            <div className="w-28">
              <label className="label">Currency</label>
              <select
                className="input-field"
                value={form.currency}
                onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}
              >
                <option value="USD">USD</option>
                <option value="IDR">IDR</option>
              </select>
            </div>
          </div>
        </div>

        {/* Horizon + Risk */}
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">Investment Profile</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Investment horizon</label>
              <select
                className="input-field"
                value={form.horizon}
                onChange={(e) => setForm((f) => ({ ...f, horizon: e.target.value as Horizon }))}
              >
                {HORIZONS.map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">
                Risk tolerance{" "}
                <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <select
                className="input-field"
                value={form.risk_tolerance}
                onChange={(e) => setForm((f) => ({ ...f, risk_tolerance: e.target.value }))}
              >
                <option value="">Auto-detect from horizon</option>
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>
          </div>
        </div>

        {/* Asset classes */}
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">Asset Classes</h2>
          <p className="text-xs text-gray-500">Select at least one. The AI will allocate across your selections.</p>
          <div className="space-y-3">
            {ASSET_CLASSES.map(({ value, label, desc }) => {
              const checked = form.asset_classes.includes(value);
              return (
                <label
                  key={value}
                  className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-colors
                    ${checked ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"}`}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 accent-blue-600"
                    checked={checked}
                    onChange={() => toggleAsset(value)}
                  />
                  <div>
                    <p className="font-medium text-sm text-gray-900">{label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3"
        >
          <Sparkles size={18} />
          {loading ? "Starting generation…" : "Generate Portfolio Report"}
        </button>

        <p className="text-xs text-center text-gray-400">
          Max 5 generations per day. For educational purposes only — not financial advice.
        </p>
      </form>
    </div>
  );
}
