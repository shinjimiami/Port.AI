import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn, formatCurrency, formatDate, RISK_COLORS, STATUS_COLORS } from "@/lib/utils";
import type { PortfolioListItem } from "@/lib/types";

interface Props {
  portfolio: PortfolioListItem;
}

export default function PortfolioCard({ portfolio }: Props) {
  return (
    <Link
      href={`/portfolio/${portfolio.id}`}
      className="block card hover:shadow-md transition-shadow group"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-gray-900">
              {formatCurrency(portfolio.budget, portfolio.currency)}
            </span>
            <span
              className={cn(
                "text-xs font-medium px-2 py-0.5 rounded-full",
                STATUS_COLORS[portfolio.status]
              )}
            >
              {portfolio.status}
            </span>
          </div>
          <p className="text-sm text-gray-500">{portfolio.horizon}</p>
          <p className="text-xs text-gray-400 mt-1">{formatDate(portfolio.created_at)}</p>
        </div>
        <ArrowRight
          size={18}
          className="text-gray-400 group-hover:text-brand-500 transition-colors mt-1"
        />
      </div>
    </Link>
  );
}
