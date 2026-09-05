import { MarketChart } from "@/components/MarketChart";
import { MARKET_LABELS, MARKET_ORDER } from "@/config/markets";
import type { Market } from "@/lib/types";

function unavailableMarket(id: (typeof MARKET_ORDER)[number]): Market {
  return {
    id,
    name: MARKET_LABELS[id],
    symbol: null,
    dataset: null,
    resolvedName: null,
    position: "",
    status: "unavailable",
    error: "Backend unavailable",
  };
}

export function MarketGrid({ markets }: { markets: Market[] }) {
  const byId = new Map(markets.map((market) => [market.id, market]));
  return (
    <main className="market-grid">
      {MARKET_ORDER.map((id) => (
        <MarketChart key={id} market={byId.get(id) ?? unavailableMarket(id)} />
      ))}
    </main>
  );
}
