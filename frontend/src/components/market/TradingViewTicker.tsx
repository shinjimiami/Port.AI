"use client";

import { useEffect, useRef } from "react";

const SYMBOLS = [
  { proName: "FOREXCOM:SPXUSD",   title: "S&P 500" },
  { proName: "NASDAQ:NDX",        title: "NASDAQ 100" },
  { proName: "FOREXCOM:DJI",      title: "Dow Jones" },
  { proName: "IDX:COMPOSITE",     title: "IDX" },
  { proName: "BITSTAMP:BTCUSD",   title: "Bitcoin" },
  { proName: "BITSTAMP:ETHUSD",   title: "Ethereum" },
  { proName: "FOREXCOM:XAUUSD",   title: "Gold" },
  { proName: "FOREXCOM:EURUSD",   title: "EUR/USD" },
  { proName: "FOREXCOM:USDJPY",   title: "USD/JPY" },
];

export default function TradingViewTicker() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.innerHTML = "";

    const widgetDiv = document.createElement("div");
    widgetDiv.className = "tradingview-widget-container__widget";
    container.appendChild(widgetDiv);

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      symbols: SYMBOLS,
      showSymbolLogo: true,
      isTransparent: false,
      displayMode: "adaptive",
      colorTheme: "light",
      locale: "en",
    });
    container.appendChild(script);

    return () => {
      if (container) container.innerHTML = "";
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-container w-full overflow-hidden rounded-xl border border-gray-200 shadow-sm"
      style={{ minHeight: 46 }}
    />
  );
}
