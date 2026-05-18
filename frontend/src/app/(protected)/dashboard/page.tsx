"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle, TrendingUp } from "lucide-react";
import { portfolioApi } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { PortfolioListItem } from "@/lib/types";
import PortfolioCard from "@/components/dashboard/PortfolioCard";

export default function DashboardPage() {
  const { user } = useAuth();
  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portfolioApi
      .history(5)
      .then(setPortfolios)
      .finally(() => setLoading(false));
  }, []);

  const completed = portfolios.filter((p) => p.status === "completed").length;
  const pending   = portfolios.filter((p) => p.status !== "completed" && p.status !== "failed").length;

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.name?.split(" ")[0]} 👋
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Here&apos;s an overview of your portfolio activity.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Portfolios</p>
          <p className="text-3xl font-bold text-gray-900">{portfolios.length}</p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Completed</p>
          <p className="text-3xl font-bold text-green-600">{completed}</p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">In progress</p>
          <p className="text-3xl font-bold text-blue-600">{pending}</p>
        </div>
      </div>

      {/* Recent portfolios */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Recent Portfolios</h2>
          <Link href="/history" className="text-sm text-brand-600 hover:underline">
            View all
          </Link>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-1/4" />
              </div>
            ))}
          </div>
        ) : portfolios.length === 0 ? (
          <div className="card text-center py-12">
            <TrendingUp className="mx-auto text-gray-300 mb-3" size={40} />
            <p className="text-gray-500 font-medium">No portfolios yet</p>
            <p className="text-gray-400 text-sm mb-4">
              Generate your first AI-powered portfolio recommendation.
            </p>
            <Link href="/generate" className="btn-primary inline-flex items-center gap-2">
              <PlusCircle size={16} />
              Generate Portfolio
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {portfolios.map((p) => (
              <PortfolioCard key={p.id} portfolio={p} />
            ))}
          </div>
        )}
      </div>

      {/* CTA */}
      {portfolios.length > 0 && (
        <Link
          href="/generate"
          className="btn-primary inline-flex items-center gap-2"
        >
          <PlusCircle size={16} />
          New Portfolio
        </Link>
      )}
    </div>
  );
}
