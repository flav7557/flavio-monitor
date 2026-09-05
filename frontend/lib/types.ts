import type { UTCTimestamp } from "lightweight-charts";

export type Market = {
  id: string;
  name: string;
  symbol: string | null;
  dataset: string | null;
  resolvedName: string | null;
  position: string;
  status: "available" | "unavailable";
  error: string | null;
};

export type Candle = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type MarketTick = {
  type: "tick";
  symbol: string;
  price: number;
  bid: number | null;
  ask: number | null;
  volume: number | null;
  timestamp: string;
};

export type StreamStatus = {
  type: "status";
  connected: boolean;
  reason?: string;
};
