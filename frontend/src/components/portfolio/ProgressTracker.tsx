"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { portfolioApi } from "@/lib/api";
import { PIPELINE_STEPS } from "@/lib/utils";
import type { PortfolioStatus } from "@/lib/types";

interface Props {
  portfolioId: number;
}

export default function ProgressTracker({ portfolioId }: Props) {
  const router = useRouter();
  const [currentNode, setCurrentNode] = useState<string>("started");
  const [status, setStatus] = useState<PortfolioStatus>("processing");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    async function poll() {
      try {
        const data = await portfolioApi.status(portfolioId);
        setStatus(data.status);

        if (data.current_node) {
          setCurrentNode(data.current_node);
        }

        if (data.status === "completed") {
          clearInterval(interval);
          setTimeout(() => router.push(`/portfolio/${portfolioId}`), 800);
        }

        if (data.status === "failed") {
          clearInterval(interval);
          setError(data.error_message ?? "Portfolio generation failed. Please try again.");
        }
      } catch {
        // Network blip — keep polling
      }
    }

    poll();
    interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [portfolioId, router]);

  const currentStepIndex = PIPELINE_STEPS.findIndex((s) => s.node === currentNode);

  return (
    <div className="card max-w-lg mx-auto">
      <div className="text-center mb-8">
        {status === "failed" ? (
          <XCircle className="mx-auto text-red-500 mb-3" size={40} />
        ) : status === "completed" ? (
          <CheckCircle className="mx-auto text-green-500 mb-3" size={40} />
        ) : (
          <Loader2 className="mx-auto text-brand-500 animate-spin mb-3" size={40} />
        )}
        <h2 className="text-lg font-semibold text-gray-900">
          {status === "completed"
            ? "Report ready! Redirecting…"
            : status === "failed"
            ? "Generation failed"
            : "Generating your portfolio…"}
        </h2>
        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      </div>

      {/* Step list */}
      <ol className="space-y-3">
        {PIPELINE_STEPS.map((step, idx) => {
          const isDone = idx < currentStepIndex;
          const isActive = idx === currentStepIndex && status !== "failed";
          const isPending = idx > currentStepIndex;

          return (
            <li key={step.node} className="flex items-center gap-3">
              {/* Icon */}
              <span
                className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
                  ${isDone ? "bg-green-100 text-green-700" : ""}
                  ${isActive ? "bg-brand-100 text-brand-700 ring-2 ring-brand-400 ring-offset-1" : ""}
                  ${isPending ? "bg-gray-100 text-gray-400" : ""}
                  ${status === "failed" && isActive ? "bg-red-100 text-red-600" : ""}
                `}
              >
                {isDone ? "✓" : idx + 1}
              </span>

              {/* Label */}
              <span
                className={`text-sm
                  ${isDone ? "text-gray-500 line-through" : ""}
                  ${isActive ? "text-gray-900 font-medium" : ""}
                  ${isPending ? "text-gray-400" : ""}
                `}
              >
                {step.label}
              </span>

              {/* Spinner on active */}
              {isActive && status === "processing" && (
                <Loader2 className="ml-auto text-brand-400 animate-spin" size={14} />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
