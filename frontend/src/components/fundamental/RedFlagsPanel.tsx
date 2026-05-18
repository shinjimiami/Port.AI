"use client";

import { AlertTriangle, CheckCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RedFlag } from "@/lib/types";

const SEVERITY_CONFIG = {
  HIGH:   { icon: AlertTriangle, bg: "bg-red-50",    border: "border-red-200",   text: "text-red-700",   badge: "bg-red-100 text-red-800" },
  MEDIUM: { icon: Info,          bg: "bg-yellow-50", border: "border-yellow-200",text: "text-yellow-700",badge: "bg-yellow-100 text-yellow-800" },
  LOW:    { icon: Info,          bg: "bg-blue-50",   border: "border-blue-200",  text: "text-blue-700",  badge: "bg-blue-100 text-blue-800" },
};

interface Props { flags: RedFlag[]; }

export default function RedFlagsPanel({ flags }: Props) {
  if (!flags.length) {
    return (
      <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
        <CheckCircle className="text-emerald-500 shrink-0" size={20} />
        <p className="text-emerald-700 text-sm font-medium">
          Tidak ditemukan red flag material dalam laporan keuangan 3 tahun terakhir.
        </p>
      </div>
    );
  }

  const high   = flags.filter((f) => f.severity === "HIGH");
  const medium = flags.filter((f) => f.severity === "MEDIUM");
  const low    = flags.filter((f) => f.severity === "LOW");

  return (
    <div className="space-y-3">
      {[...high, ...medium, ...low].map((flag, i) => {
        const cfg = SEVERITY_CONFIG[flag.severity] ?? SEVERITY_CONFIG.LOW;
        const Icon = cfg.icon;
        return (
          <div key={i} className={cn("flex gap-3 p-4 rounded-lg border", cfg.bg, cfg.border)}>
            <Icon className={cn("shrink-0 mt-0.5", cfg.text)} size={18} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className={cn("text-xs font-bold px-2 py-0.5 rounded-full", cfg.badge)}>
                  {flag.severity}
                </span>
                <span className="text-xs font-semibold text-gray-500">{flag.category}</span>
              </div>
              <p className={cn("text-sm", cfg.text)}>{flag.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
