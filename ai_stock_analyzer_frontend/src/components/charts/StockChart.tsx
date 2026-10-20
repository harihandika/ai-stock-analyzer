"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";
import { formatPrice } from "@/services/market";

export interface ChartData {
  time: string; // 'YYYY-MM-DD'
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  ema20?: number | null;
  ema50?: number | null;
  ema200?: number | null;
  rsi?: number | null;
  macd?: number | null;
  macdSignal?: number | null;
  stoppingVolume?: boolean;
  noDemand?: boolean;
  isSpring?: boolean;
  climacticVolume?: boolean;
}

interface StockChartProps {
  data: ChartData[];
  width?: number;
  height?: number;
  currency?: string | null;
  focusDate?: string | null;
}

export function StockChart({
  data,
  width = 0,
  height = 400,
  currency,
  focusDate,
}: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const rsiContainerRef = useRef<HTMLDivElement>(null);
  const macdContainerRef = useRef<HTMLDivElement>(null);

  const [hover, setHover] = useState<{
    source: ChartData[];
    point: ChartData;
  } | null>(null);
  const legendData =
    hover?.source === data
      ? hover.point
      : data.find((point) => point.time === focusDate) || data.at(-1) || null;
  const hasRsi = data.some((d) => d.rsi != null);
  const hasMacd = data.some((d) => d.macd != null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Default width if not specified
    const currentWidth = width || chartContainerRef.current.clientWidth;

    const commonOptions = {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
      },
      handleScroll: {
        mouseWheel: false,
        pressedMouseMove: true,
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.1)",
        rightOffset: 12,
        barSpacing: 10,
        fixLeftEdge: true,
      },
      crosshair: {
        mode: 1, // Normal mode
        vertLine: {
          color: "rgba(224, 227, 235, 0.4)",
          width: 1 as const,
          style: 1 as const,
          labelBackgroundColor: "#1e222d",
        },
        horzLine: {
          color: "rgba(224, 227, 235, 0.4)",
          width: 1 as const,
          style: 1 as const,
          labelBackgroundColor: "#1e222d",
        },
      },
    };

    // --- Main Chart ---
    const chart = createChart(chartContainerRef.current, {
      ...commonOptions,
      width: currentWidth,
      height: height,
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.1)",
        autoScale: true,
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#f43f5e",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
    });
    candlestickSeries.setData(
      data.map((d) => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })),
    );

    // Set markers on the candlestick series (Not natively supported in lightweight-charts v5 without plugins)
    // We will just show these in the legend instead.

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    chart.priceScale("").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(
      data.map((d) => ({
        time: d.time,
        value: d.volume || 0,
        color:
          d.close >= d.open
            ? "rgba(16, 185, 129, 0.3)"
            : "rgba(244, 63, 94, 0.3)",
      })),
    );

    const createEmaSeries = (color: string) =>
      chart.addSeries(LineSeries, {
        color,
        lineWidth: 2,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
    const ema20Series = createEmaSeries("#eab308");
    const ema50Series = createEmaSeries("#3b82f6");
    const ema200Series = createEmaSeries("#ef4444");

    const ema20Data = data
      .filter((d) => d.ema20 != null)
      .map((d) => ({ time: d.time, value: d.ema20! }));
    const ema50Data = data
      .filter((d) => d.ema50 != null)
      .map((d) => ({ time: d.time, value: d.ema50! }));
    const ema200Data = data
      .filter((d) => d.ema200 != null)
      .map((d) => ({ time: d.time, value: d.ema200! }));

    if (ema20Data.length > 0) ema20Series.setData(ema20Data);
    if (ema50Data.length > 0) ema50Series.setData(ema50Data);
    if (ema200Data.length > 0) ema200Series.setData(ema200Data);

    // --- RSI Chart ---
    let rsiChart: IChartApi | null = null;
    if (hasRsi && rsiContainerRef.current) {
      rsiChart = createChart(rsiContainerRef.current, {
        ...commonOptions,
        width: currentWidth,
        height: 120,
        rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      });
      const rsiSeries = rsiChart.addSeries(LineSeries, {
        color: "#a855f7",
        lineWidth: 2,
      });
      rsiSeries.setData(
        data
          .filter((d) => d.rsi != null)
          .map((d) => ({ time: d.time, value: d.rsi! })),
      );

      // Overbought / Oversold lines
      const overboughtSeries = rsiChart.addSeries(LineSeries, {
        color: "rgba(244, 63, 94, 0.3)",
        lineWidth: 1,
        lineStyle: 2,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      const oversoldSeries = rsiChart.addSeries(LineSeries, {
        color: "rgba(16, 185, 129, 0.3)",
        lineWidth: 1,
        lineStyle: 2,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      overboughtSeries.setData(data.map((d) => ({ time: d.time, value: 70 })));
      oversoldSeries.setData(data.map((d) => ({ time: d.time, value: 30 })));
    }

    // --- MACD Chart ---
    let macdChart: IChartApi | null = null;
    if (hasMacd && macdContainerRef.current) {
      macdChart = createChart(macdContainerRef.current, {
        ...commonOptions,
        width: currentWidth,
        height: 120,
        rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      });
      const macdHist = macdChart.addSeries(HistogramSeries, {
        color: "#38bdf8",
      });
      macdHist.setData(
        data
          .filter((d) => d.macd != null && d.macdSignal != null)
          .map((d) => ({
            time: d.time,
            value: d.macd! - d.macdSignal!,
            color:
              d.macd! - d.macdSignal! >= 0
                ? "rgba(16, 185, 129, 0.6)"
                : "rgba(244, 63, 94, 0.6)",
          })),
      );

      const macdLine = macdChart.addSeries(LineSeries, {
        color: "#38bdf8",
        lineWidth: 2,
      });
      macdLine.setData(
        data
          .filter((d) => d.macd != null)
          .map((d) => ({ time: d.time, value: d.macd! })),
      );

      const macdSignalLine = macdChart.addSeries(LineSeries, {
        color: "#fb923c",
        lineWidth: 2,
      });
      macdSignalLine.setData(
        data
          .filter((d) => d.macdSignal != null)
          .map((d) => ({ time: d.time, value: d.macdSignal! })),
      );
    }

    // Sync Crosshair and TimeScale
    const charts = [chart, rsiChart, macdChart].filter(Boolean) as IChartApi[];

    charts.forEach((c) => {
      c.subscribeClick((param) => {
        const point = data.find((d) => d.time === param.time);
        if (point) setHover({ source: data, point });
      });
      c.subscribeCrosshairMove((param) => {
        if (param.point && param.time) {
          const currentData = data.find((d) => d.time === param.time);
          if (currentData) setHover({ source: data, point: currentData });
        }
      });
    });
    let syncingRange = false;
    charts.forEach((c) =>
      c.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (!range || syncingRange) return;
        syncingRange = true;
        charts.forEach((other) => {
          if (other !== c) other.timeScale().setVisibleLogicalRange(range);
        });
        syncingRange = false;
      }),
    );
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current && !width) {
        charts.forEach((c) => {
          c.applyOptions({ width: chartContainerRef.current!.clientWidth });
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      charts.forEach((c) => c.remove());
    };
  }, [data, width, height, hasRsi, hasMacd]);

  const selectedIndex = legendData ? data.indexOf(legendData) : 0;
  const indicator = (value: number | null | undefined) =>
    value == null
      ? "Belum tersedia"
      : value.toLocaleString("id-ID", { maximumFractionDigits: 4 });
  return (
    <div className="w-full min-w-0 flex flex-col gap-4">
      <div
        ref={chartContainerRef}
        className="w-full min-w-0"
        style={{ height }}
      />
      {legendData && (
        <section
          aria-label="Nilai candle dan indikator"
          className="rounded border border-slate-700 bg-slate-900/80 p-3 space-y-3"
          data-testid="candle-values"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p>
              Candle{" "}
              <time dateTime={legendData.time} data-testid="candle-date">
                {legendData.time}
              </time>{" "}
              · {currency || "Currency belum terverifikasi"}
            </p>
            <button
              type="button"
              className="rounded border border-slate-600 px-3 py-2"
              onClick={() =>
                setHover({ source: data, point: data[data.length - 1] })
              }
            >
              Candle terbaru
            </button>
          </div>
          <label className="block space-y-1">
            <span>Pilih candle</span>
            <input
              aria-label="Pilih candle"
              aria-valuetext={legendData.time}
              type="range"
              className="w-full min-h-11"
              min={0}
              max={data.length - 1}
              value={selectedIndex}
              onChange={(e) =>
                setHover({ source: data, point: data[Number(e.target.value)] })
              }
            />
          </label>
          <dl className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-2 text-sm">
            {[
              ["Open", formatPrice(legendData.open, currency)],
              ["High", formatPrice(legendData.high, currency)],
              ["Low", formatPrice(legendData.low, currency)],
              ["Close", formatPrice(legendData.close, currency)],
              ["Volume (lembar)", indicator(legendData.volume)],
              [
                "EMA (20)",
                legendData.ema20 == null
                  ? "Belum tersedia"
                  : formatPrice(legendData.ema20, currency),
              ],
              [
                "EMA (50)",
                legendData.ema50 == null
                  ? "Belum tersedia"
                  : formatPrice(legendData.ema50, currency),
              ],
              [
                "EMA (200)",
                legendData.ema200 == null
                  ? "Belum tersedia"
                  : formatPrice(legendData.ema200, currency),
              ],
              ["RSI (14)", indicator(legendData.rsi)],
              ["MACD", indicator(legendData.macd)],
              ["MACD signal", indicator(legendData.macdSignal)],
            ].map(([label, value]) => (
              <div key={label} className="min-w-0">
                <dt className="text-slate-400">{label}</dt>
                <dd className="break-words font-mono" data-value={label}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
          <div className="flex flex-wrap gap-2 text-xs">
            {legendData.stoppingVolume && <span>Stopping Volume</span>}
            {legendData.isSpring && <span>Spring</span>}
            {legendData.noDemand && <span>No Demand</span>}
            {legendData.climacticVolume && <span>Climactic Volume</span>}
          </div>
        </section>
      )}
      {hasRsi && <div ref={rsiContainerRef} className="w-full h-[120px]" />}
      {hasMacd && <div ref={macdContainerRef} className="w-full h-[120px]" />}
    </div>
  );
}
