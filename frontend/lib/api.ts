import type { Candle, Market } from "@/lib/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { signal, cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getMarkets(signal?: AbortSignal): Promise<Market[]> {
  return request<Market[]>("/api/markets", signal);
}

export async function getCandles(
  symbol: string,
  timeframe: string,
  limit = 300,
  signal?: AbortSignal,
): Promise<Candle[]> {
  const payload = await request<{ candles: Candle[] }>(
    `/api/candles/${encodeURIComponent(symbol)}?timeframe=${timeframe}&limit=${limit}`,
    signal,
  );
  return payload.candles;
}

export function websocketUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const url = new URL(API_BASE);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/markets";
  url.search = "";
  return url.toString();
}
