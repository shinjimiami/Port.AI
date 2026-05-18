import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export const ASSET_CLASS_LABELS: Record<string, string> = {
  US_STOCKS: "US Stocks",
  IDX: "IDX Stocks",
  CRYPTO: "Crypto",
};

export const RISK_COLORS: Record<string, string> = {
  conservative: "bg-green-100 text-green-800",
  moderate:     "bg-yellow-100 text-yellow-800",
  aggressive:   "bg-red-100 text-red-800",
  Low:          "bg-green-100 text-green-800",
  Moderate:     "bg-yellow-100 text-yellow-800",
  High:         "bg-red-100 text-red-800",
};

export const STATUS_COLORS: Record<string, string> = {
  pending:    "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  completed:  "bg-green-100 text-green-700",
  failed:     "bg-red-100 text-red-700",
};

export const CHART_COLORS = [
  "#3B82F6", // blue-500
  "#10B981", // emerald-500
  "#F59E0B", // amber-500
  "#8B5CF6", // violet-500
  "#EC4899", // pink-500
  "#EF4444", // red-500
];

export const PIPELINE_STEPS = [
  { node: "started",               label: "Starting" },
  { node: "input_validator",       label: "Validating preferences" },
  { node: "market_data_fetcher",   label: "Fetching market data" },
  { node: "allocation_planner",    label: "Planning allocation" },
  { node: "asset_selector",        label: "Selecting assets" },
  { node: "diversification_checker", label: "Checking diversification" },
  { node: "report_generator",      label: "Generating report" },
  { node: "completed",             label: "Done!" },
];
