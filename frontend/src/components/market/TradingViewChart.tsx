"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

const SYMBOLS = [
  { label: "S&P 500",   value: "FOREXCOM:SPXUSD" },
  { label: "NASDAQ",    value: "NASDAQ:NDX" },
  { label: "Dow Jones", value: "FOREXCOM:DJI" },
  { label: "IDX",       value: "IDX:COMPOSITE" },
  { label: "Bitcoin",   value: "BITSTAMP:BTCUSD" },
  { label: "Ethereum",  value: "BITSTAMP:ETHUSD" },
  { label: "Gold",      value: "FOREXCOM:XAUUSD" },
  { label: "EUR/USD",   value: "FX:EURUSD" },
];

export default function TradingViewChart() {
  const [activeSymbol, setActiveSymbol] = useState(SYMBOLS[0].value);
  const widgetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const widget = widgetRef.current;
    if (!widget) return;

    widget.innerHTML = "";

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: activeSymbol,
      interval: "D",
      timezone: "Asia/Jakarta",
      theme: "light",
      style: "1",
      locale: "en",
      withdateranges: true,
      hide_side_toolbar: false,
      allow_symbol_change: false,
      calendar: false,
      support_host: "https://www.tradingview.com",
    });
    widget.appendChild(script);

    return () => {
      if (widget) widget.innerHTML = "";
    };
  }, [activeSymbol]);

  return (
    <div className="card">
      {/* Symbol tabs */}
      <div className="flex items-center gap-1.5 mb-4 flex-wrap">
        {SYMBOLS.map((s) => (
          <button
            key={s.value}
            onClick={() => setActiveSymbol(s.value)}
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-semibold transition-all",
              activeSymbol === s.value
                ? "bg-brand-600 text-white shadow-sm"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Chart container */}
      <div
        ref={widgetRef}
        className="tradingview-widget-container w-full rounded-lg overflow-hidden"
        style={{ height: 440 }}
      />

      <p className="text-xs text-gray-400 mt-2 text-right">
        Powered by{" "}
        <a
          href="https://www.tradingview.com"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-brand-500 underline"
        >
          TradingView
        </a>
      </p>
    </div>
  );
}
