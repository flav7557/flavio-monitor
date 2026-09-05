import type { UTCTimestamp } from "lightweight-charts";
import type { Candle, MarketTick } from "@/lib/types";
import type { Timeframe } from "@/config/markets";

const SECONDS: Record<Timeframe, number> = {
  "1m": 60,
  "5m": 300,
  "15m": 900,
  "1h": 3600,
  "4h": 14400,
  "1D": 86400,
};

function candleTime(timestamp: string, timeframe: Timeframe): UTCTimestamp {
  const epoch = Math.floor(new Date(timestamp).getTime() / 1000);
  const interval = SECONDS[timeframe];
  return (Math.floor(epoch / interval) * interval) as UTCTimestamp;
}

export function aggregateTick(
  current: Candle | null,
  tick: MarketTick,
  timeframe: Timeframe,
): Candle {
  const time = candleTime(tick.timestamp, timeframe);
  const volume = tick.volume ?? 0;
  if (!current || current.time !== time) {
    return {
      time,
      open: tick.price,
      high: tick.price,
      low: tick.price,
      close: tick.price,
      volume,
    };
  }
  return {
    ...current,
    high: Math.max(current.high, tick.price),
    low: Math.min(current.low, tick.price),
    close: tick.price,
    volume: current.volume + volume,
  };
}
