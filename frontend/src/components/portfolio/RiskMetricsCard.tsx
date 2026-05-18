import { cn, RISK_COLORS } from "@/lib/utils";
import type { RiskMetrics } from "@/lib/types";

interface Props {
  metrics: RiskMetrics;
}

const METRIC_ROWS = [
  { key: "expected_return",       label: "Expected return" },
  { key: "max_drawdown_estimate", label: "Max drawdown" },
  { key: "sharpe_estimate",       label: "Sharpe ratio" },
] as const;

export default function RiskMetricsCard({ metrics }: Props) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Risk & Return</h3>
        <span
          className={cn(
            "text-xs font-medium px-2.5 py-1 rounded-full",
            RISK_COLORS[metrics.risk_level] ?? "bg-gray-100 text-gray-700"
          )}
        >
          {metrics.risk_level} Risk
        </span>
      </div>

      <div className="space-y-3">
        {METRIC_ROWS.map(({ key, label }) => {
          const val = metrics[key];
          if (!val) return null;
          return (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-gray-500">{label}</span>
              <span className="font-medium text-gray-900">{val}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
