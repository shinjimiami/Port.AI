"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, PlusCircle } from "lucide-react";
import { portfolioApi } from "@/lib/api";
import type { PortfolioListItem } from "@/lib/types";
import PortfolioCard from "@/components/dashboard/PortfolioCard";

const PAGE_SIZE = 10;

export default function HistoryPage() {
  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    setLoading(true);
    portfolioApi
      .history(PAGE_SIZE, page * PAGE_SIZE)
      .then((data) => {
        setPortfolios(data);
        setHasMore(data.length === PAGE_SIZE);
      })
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio History</h1>
          <p className="text-gray-500 text-sm mt-1">All your past portfolio generations.</p>
        </div>
        <Link href="/generate" className="btn-primary flex items-center gap-2 text-sm">
          <PlusCircle size={15} />
          New
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : portfolios.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500 font-medium">No portfolios on this page.</p>
          {page > 0 && (
            <button
              onClick={() => setPage(0)}
              className="btn-secondary mt-4 text-sm"
            >
              Back to start
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {portfolios.map((p) => (
            <PortfolioCard key={p.id} portfolio={p} />
          ))}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="btn-secondary flex items-center gap-1 text-sm disabled:opacity-40"
        >
          <ChevronLeft size={16} /> Previous
        </button>
        <span className="text-sm text-gray-500">Page {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={!hasMore}
          className="btn-secondary flex items-center gap-1 text-sm disabled:opacity-40"
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
