"use client";

import { useEffect, useState } from "react";
import { MarketGrid } from "@/components/MarketGrid";
import { MarketHeader } from "@/components/MarketHeader";
import { MarketStreamProvider, useMarketStream } from "@/hooks/useMarketStream";
import { getMarkets } from "@/lib/api";
import type { Market } from "@/lib/types";

function TerminalSurface() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const { connected } = useMarketStream();

  useEffect(() => {
    const controller = new AbortController();
    getMarkets(controller.signal).then(setMarkets).catch(() => setMarkets([]));
    return () => controller.abort();
  }, []);

  return (
    <div className="terminal-shell">
      <MarketHeader connected={connected} />
      <MarketGrid markets={markets} />
    </div>
  );
}

export function MarketTerminal() {
  return (
    <MarketStreamProvider>
      <TerminalSurface />
    </MarketStreamProvider>
  );
}
