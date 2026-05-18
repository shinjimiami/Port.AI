import { Calendar } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { RebalancingInfo } from "@/lib/types";

interface Props {
  rebalancing: RebalancingInfo;
}

export default function RebalancingCard({ rebalancing }: Props) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Calendar size={18} className="text-brand-500" />
        <h3 className="font-semibold text-gray-900">Rebalancing Plan</h3>
      </div>

      {rebalancing.suggested_date && (
        <div className="mb-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Suggested review date</p>
          <p className="text-base font-semibold text-gray-900">
            {formatDate(rebalancing.suggested_date)}
          </p>
        </div>
      )}

      {rebalancing.trigger_conditions.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Review triggers</p>
          <ul className="space-y-2">
            {rebalancing.trigger_conditions.map((condition, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-brand-500 font-bold mt-0.5">→</span>
                {condition}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
