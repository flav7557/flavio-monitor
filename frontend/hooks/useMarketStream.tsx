"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { websocketUrl } from "@/lib/api";
import type { MarketTick, StreamStatus } from "@/lib/types";

type TickListener = (tick: MarketTick) => void;

type MarketStreamContextValue = {
  connected: boolean;
  subscribe: (symbol: string, listener: TickListener) => () => void;
};

const MarketStreamContext = createContext<MarketStreamContextValue | null>(null);

export function MarketStreamProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const listeners = useRef(new Map<string, Set<TickListener>>());

  const subscribe = useCallback((symbol: string, listener: TickListener) => {
    const symbolListeners = listeners.current.get(symbol) ?? new Set<TickListener>();
    symbolListeners.add(listener);
    listeners.current.set(symbol, symbolListeners);
    return () => {
      symbolListeners.delete(listener);
      if (!symbolListeners.size) listeners.current.delete(symbol);
    };
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;
    let backoff = 1000;

    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(websocketUrl());
      socket.onopen = () => {
        backoff = 1000;
      };
      socket.onmessage = (event) => {
        let message: MarketTick | StreamStatus;
        try {
          message = JSON.parse(event.data) as MarketTick | StreamStatus;
        } catch {
          return;
        }
        if (message.type === "status") {
          setConnected(message.connected);
          return;
        }
        listeners.current.get(message.symbol)?.forEach((listener) => listener(message));
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) {
          retryTimer = setTimeout(connect, backoff);
          backoff = Math.min(backoff * 2, 30000);
        }
      };
    };

    connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  const value = useMemo(() => ({ connected, subscribe }), [connected, subscribe]);
  return <MarketStreamContext.Provider value={value}>{children}</MarketStreamContext.Provider>;
}

export function useMarketStream() {
  const context = useContext(MarketStreamContext);
  if (!context) throw new Error("useMarketStream must be used inside MarketStreamProvider");
  return context;
}
