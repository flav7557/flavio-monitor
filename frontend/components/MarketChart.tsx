"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { TimeframeSelector } from "@/components/TimeframeSelector";
import { toLseTimeframe, type Timeframe } from "@/config/markets";
import { useMarketStream } from "@/hooks/useMarketStream";
import { getCandles } from "@/lib/api";
import { aggregateTick } from "@/lib/candleAggregator";
import type { Candle, Market, MarketTick } from "@/lib/types";

const UP = "#37b57b";
const DOWN = "#e05f65";

function formatPrice(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function MarketChart({ market }: { market: Market }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("5m");
  const [loading, setLoading] = useState(Boolean(market.symbol));
  const [error, setError] = useState<string | null>(market.error);
  const chartElement = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lastCandle = useRef<Candle | null>(null);
  const previousClose = useRef<number | null>(null);
  const priceElement = useRef<HTMLSpanElement>(null);
  const changeElement = useRef<HTMLSpanElement>(null);
  const ohlcElement = useRef<HTMLDivElement>(null);
  const timeframeRef = useRef<Timeframe>(timeframe);
  const { subscribe } = useMarketStream();

  const updateQuote = useCallback((price: number) => {
    if (priceElement.current) priceElement.current.textContent = formatPrice(price);
    const previous = previousClose.current;
    const change = previous && previous !== 0 ? ((price / previous) - 1) * 100 : null;
    if (changeElement.current) {
      changeElement.current.textContent = formatPercent(change);
      changeElement.current.dataset.direction = change === null ? "flat" : change >= 0 ? "up" : "down";
    }
  }, []);

  useEffect(() => {
    if (!chartElement.current) return;
    const instance = createChart(chartElement.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0a0a0a" },
        textColor: "#686b70",
        fontFamily: '"Segoe UI", Arial, sans-serif',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.025)" },
        horzLines: { color: "rgba(255,255,255,0.025)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(255,255,255,0.22)", width: 1, style: 2, labelVisible: false },
        horzLine: { color: "rgba(255,255,255,0.22)", width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.07)",
        scaleMargins: { top: 0.12, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.07)",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 4,
        barSpacing: 6,
        minBarSpacing: 2,
      },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
    });
    const candleSeries = instance.addSeries(CandlestickSeries, {
      upColor: UP,
      downColor: DOWN,
      borderVisible: false,
      wickUpColor: UP,
      wickDownColor: DOWN,
      priceLineVisible: true,
      priceLineWidth: 1,
      lastValueVisible: true,
    });
    instance.subscribeCrosshairMove((param) => {
      const data = param.seriesData.get(candleSeries) as CandlestickData<UTCTimestamp> | undefined;
      if (!ohlcElement.current) return;
      if (!data || !("open" in data)) {
        ohlcElement.current.dataset.visible = "false";
        return;
      }
      ohlcElement.current.dataset.visible = "true";
      ohlcElement.current.innerHTML = [
        ["O", data.open],
        ["H", data.high],
        ["L", data.low],
        ["C", data.close],
      ].map(([label, value]) => `<span><b>${label}</b> ${formatPrice(Number(value))}</span>`).join("");
    });
    chart.current = instance;
    series.current = candleSeries;
    return () => {
      instance.remove();
      chart.current = null;
      series.current = null;
    };
  }, []);

  useEffect(() => {
    timeframeRef.current = timeframe;
    if (!market.symbol || !series.current) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      getCandles(market.symbol, toLseTimeframe(timeframe), 300, controller.signal),
      getCandles(market.symbol, "1d", 2, controller.signal),
    ])
      .then(([candles, daily]) => {
        if (!series.current) return;
        series.current.setData(candles);
        lastCandle.current = candles.at(-1) ?? null;
        previousClose.current = daily.length > 1 ? daily.at(-2)?.close ?? null : daily[0]?.close ?? null;
        const latest = candles.at(-1)?.close ?? daily.at(-1)?.close ?? null;
        if (latest !== null) updateQuote(latest);
        chart.current?.timeScale().fitContent();
      })
      .catch((reason: Error) => {
        if (reason.name !== "AbortError") setError(reason.message || "London Strategic Edge unavailable");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [market.symbol, timeframe, updateQuote]);

  useEffect(() => {
    if (!market.symbol) return;
    return subscribe(market.symbol, (tick: MarketTick) => {
      const next = aggregateTick(lastCandle.current, tick, timeframeRef.current);
      lastCandle.current = next;
      series.current?.update(next);
      updateQuote(tick.price);
    });
  }, [market.symbol, subscribe, updateQuote]);

  return (
    <section className="market-panel" aria-label={`${market.name} market chart`}>
      <div className="panel-topbar">
        <div className="market-identity">
          <div className="market-title-row">
            <h2>{market.name}</h2>
            <span className="market-meta">{market.symbol ?? "UNRESOLVED"} · {timeframe}</span>
          </div>
          <div className="quote-row">
            <span ref={priceElement} className="market-price">—</span>
            <span ref={changeElement} className="market-change" data-direction="flat">—</span>
          </div>
        </div>
        <TimeframeSelector value={timeframe} onChange={setTimeframe} />
      </div>
      <div ref={ohlcElement} className="ohlc" data-visible="false" />
      <div ref={chartElement} className="chart-surface" />
      {(loading || error || !market.symbol) && (
        <div className="chart-state" role="status">
          {loading ? "Loading LSE data" : error || "Symbol unavailable"}
        </div>
      )}
    </section>
  );
}
