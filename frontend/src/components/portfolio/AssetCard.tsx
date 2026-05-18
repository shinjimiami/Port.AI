import { TrendingUp } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import type { AssetItem } from "@/lib/types";

interface Props {
  asset: AssetItem;
  currency: string;
}

const CLASS_BADGE: Record<string, string> = {
  US_STOCKS: "bg-blue-50 text-blue-700",
  IDX:       "bg-green-50 text-green-700",
  CRYPTO:    "bg-purple-50 text-purple-700",
};

export default function AssetCard({ asset, currency }: Props) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg font-bold text-gray-900">{asset.ticker}</span>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full
                ${CLASS_BADGE[asset.asset_class] ?? "bg-gray-100 text-gray-600"}`}
            >
              {asset.asset_class.replace("_", " ")}
            </span>
          </div>
          <p className="text-sm text-gray-500">{asset.name}</p>
          {asset.sector && (
            <p className="text-xs text-gray-400 mt-0.5">{asset.sector}</p>
          )}
        </div>

        <div className="text-right">
          <p className="text-lg font-bold text-gray-900">{asset.allocation_percentage}%</p>
          <p className="text-xs text-gray-500">{formatCurrency(asset.amount, currency)}</p>
        </div>
      </div>

      {/* Metrics row */}
      <div className="flex items-center gap-4 text-xs text-gray-600 mb-3 border-t border-gray-50 pt-3">
        {asset.current_price != null && (
          <div>
            <span className="text-gray-400">Price</span>
            <p className="font-medium text-gray-800">
              {formatCurrency(asset.current_price, currency === "IDR" ? "IDR" : "USD")}
            </p>
          </div>
        )}
        {asset.expected_return && (
          <div className="flex items-center gap-1">
            <TrendingUp size={12} className="text-green-500" />
            <div>
              <span className="text-gray-400">Expected return</span>
              <p className="font-medium text-green-700">{asset.expected_return}</p>
            </div>
          </div>
        )}
      </div>

      {/* Reasoning */}
      <p className="text-xs text-gray-600 leading-relaxed">{asset.reasoning}</p>
    </div>
  );
}
