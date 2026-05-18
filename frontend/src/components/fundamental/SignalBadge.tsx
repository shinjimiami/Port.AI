"use client";

import { cn } from "@/lib/utils";
import type { SignalKey } from "@/lib/types";

const SIGNAL_STYLES: Record<SignalKey, string> = {
  STRONG_BUY:   "bg-emerald-100 text-emerald-800 border-emerald-300",
  BUY:          "bg-green-100  text-green-800  border-green-300",
  MODERATE_BUY: "bg-yellow-100 text-yellow-800 border-yellow-300",
  NEUTRAL:      "bg-orange-100 text-orange-800 border-orange-300",
  AVOID:        "bg-red-100    text-red-800    border-red-300",
};

interface Props {
  signalKey: SignalKey;
  label: string;
  score: number;
  size?: "sm" | "lg";
}

export default function SignalBadge({ signalKey, label, score, size = "lg" }: Props) {
  return (
    <div className={cn("inline-flex flex-col items-center gap-1", size === "lg" ? "p-4" : "p-2")}>
      <span className={cn(
        "font-bold border rounded-full tracking-wide",
        size === "lg" ? "text-xl px-6 py-2" : "text-sm px-3 py-1",
        SIGNAL_STYLES[signalKey] ?? SIGNAL_STYLES.NEUTRAL,
      )}>
        {label}
      </span>
      <span className={cn("text-gray-500 font-medium", size === "lg" ? "text-sm" : "text-xs")}>
        Score: <span className="text-gray-900 font-bold">{score.toFixed(1)}</span>/100
      </span>
    </div>
  );
}
