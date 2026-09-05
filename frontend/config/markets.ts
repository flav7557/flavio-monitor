export const MARKET_ORDER = ["cac40", "gold", "sp500", "asx5", "oil", "nasdaq"] as const;

export const MARKET_LABELS: Record<(typeof MARKET_ORDER)[number], string> = {
  cac40: "CAC 40",
  gold: "GOLD",
  sp500: "S&P 500",
  asx5: "ASX 5",
  oil: "OIL",
  nasdaq: "NASDAQ",
};

export const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"] as const;
export type Timeframe = (typeof TIMEFRAMES)[number];

export function toLseTimeframe(timeframe: Timeframe): string {
  return timeframe === "1D" ? "1d" : timeframe;
}
