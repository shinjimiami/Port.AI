"use client";

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { CHART_COLORS, formatCurrency } from "@/lib/utils";
import type { AllocationItem } from "@/lib/types";

interface Props {
  allocation: AllocationItem[];
  currency: string;
}

export default function AllocationPieChart({ allocation, currency }: Props) {
  const data = allocation.map((item) => ({
    name: item.asset_class.replace("_", " "),
    value: item.percentage,
    amount: item.amount,
  }));

  return (
    <div className="card">
      <h3 className="font-semibold text-gray-900 mb-4">Allocation Breakdown</h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={3}
            dataKey="value"
            label={({ name, value }) => `${name} ${value}%`}
            labelLine={false}
          >
            {data.map((_, index) => (
              <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string, props) => [
              `${value}% (${formatCurrency(props.payload.amount, currency)})`,
              name,
            ]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>

      {/* Table breakdown */}
      <div className="mt-4 space-y-2">
        {allocation.map((item, idx) => (
          <div key={item.asset_class} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
              />
              <span className="text-gray-700">{item.asset_class.replace("_", " ")}</span>
            </div>
            <div className="text-right">
              <span className="font-medium text-gray-900">{item.percentage}%</span>
              <span className="text-gray-400 ml-2 text-xs">
                {formatCurrency(item.amount, currency)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
