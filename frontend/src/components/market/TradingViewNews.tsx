"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

const FEEDS = [
  { label: "All Markets", mode: "all_symbols", symbol: undefined },
  { label: "S&P 500",     mode: "symbol",      symbol: "FOREXCOM:SPXUSD" },
  { label: "NASDAQ",      mode: "symbol",      symbol: "NASDAQ:NDX" },
  { label: "IDX",         mode: "symbol",      symbol: "IDX:COMPOSITE" },
  { label: "Bitcoin",     mode: "symbol",      symbol: "BITSTAMP:BTCUSD" },
  { label: "Gold",        mode: "symbol",      symbol: "FOREXCOM:XAUUSD" },
] as const;

export default function TradingViewNews() {
  const [active, setActive] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = "";

    const feed = FEEDS[active];
    const config: Record<string, unknown> = {
      colorTheme: "light",
      isTransparent: false,
      displayMode: "regular",
      width: "100%",
      height: 480,
      locale: "en",
      feedMode: feed.mode,
    };
    if (feed.symbol) config["symbol"] = feed.symbol;

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-timeline.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify(config);
    container.appendChild(script);

    return () => {
      if (container) container.innerHTML = "";
    };
  }, [active]);

  return (
    <div className="card flex flex-col">
      {/* Feed selector */}
      <div className="flex items-center gap-1.5 mb-4 flex-wrap">
        {FEEDS.map((f, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-semibold transition-all",
              active === i
                ? "bg-brand-600 text-white shadow-sm"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* TradingView Timeline widget */}
      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />
    </div>
  );
}
