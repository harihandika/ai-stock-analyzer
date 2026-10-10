'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';
import clsx from 'clsx';

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
}

export function StockChart({ data, width = 0, height = 400 }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const rsiContainerRef = useRef<HTMLDivElement>(null);
  const macdContainerRef = useRef<HTMLDivElement>(null);
  
  const [legendData, setLegendData] = useState<ChartData | null>(null);

  // Check if we have indicators to show
  const hasRsi = data.some(d => d.rsi != null);
  const hasMacd = data.some(d => d.macd != null);

  // Set latest data as initial legend
  useEffect(() => {
    if (data && data.length > 0) {
      setLegendData(data[data.length - 1]);
    }
  }, [data]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Default width if not specified
    const currentWidth = width || chartContainerRef.current.clientWidth;

    const commonOptions = {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.05)' },
        horzLines: { color: 'rgba(255,255,255,0.05)' },
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
        borderColor: 'rgba(255,255,255,0.1)',
        rightOffset: 12,
        barSpacing: 10,
        fixLeftEdge: true,
      },
      crosshair: {
        mode: 1, // Normal mode
        vertLine: { color: 'rgba(224, 227, 235, 0.4)', width: 1 as const, style: 1 as const, labelBackgroundColor: '#1e222d' },
        horzLine: { color: 'rgba(224, 227, 235, 0.4)', width: 1 as const, style: 1 as const, labelBackgroundColor: '#1e222d' },
      }
    };

    // --- Main Chart ---
    const chart = createChart(chartContainerRef.current, {
      ...commonOptions,
      width: currentWidth,
      height: height,
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.1)',
        autoScale: true,
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#f43f5e',
    });
    candlestickSeries.setData(data.map(d => ({
      time: d.time, open: d.open, high: d.high, low: d.low, close: d.close,
    })));

    // Set markers on the candlestick series (Not natively supported in lightweight-charts v5 without plugins)
    // We will just show these in the legend instead.

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: '', 
    });
    chart.priceScale('').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(data.map(d => ({
      time: d.time,
      value: d.volume || 0,
      color: d.close >= d.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'
    })));

    const createEmaSeries = (color: string) => chart.addSeries(LineSeries, {
      color, lineWidth: 1.5, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
    });
    const ema20Series = createEmaSeries('#eab308');
    const ema50Series = createEmaSeries('#3b82f6');
    const ema200Series = createEmaSeries('#ef4444');

    const ema20Data = data.filter(d => d.ema20 != null).map(d => ({ time: d.time, value: d.ema20! }));
    const ema50Data = data.filter(d => d.ema50 != null).map(d => ({ time: d.time, value: d.ema50! }));
    const ema200Data = data.filter(d => d.ema200 != null).map(d => ({ time: d.time, value: d.ema200! }));

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
        rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
      });
      const rsiSeries = rsiChart.addSeries(LineSeries, { color: '#a855f7', lineWidth: 1.5 });
      rsiSeries.setData(data.filter(d => d.rsi != null).map(d => ({ time: d.time, value: d.rsi! })));
      
      // Overbought / Oversold lines
      const overboughtSeries = rsiChart.addSeries(LineSeries, { color: 'rgba(244, 63, 94, 0.3)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
      const oversoldSeries = rsiChart.addSeries(LineSeries, { color: 'rgba(16, 185, 129, 0.3)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false });
      overboughtSeries.setData(data.map(d => ({ time: d.time, value: 70 })));
      oversoldSeries.setData(data.map(d => ({ time: d.time, value: 30 })));
    }

    // --- MACD Chart ---
    let macdChart: IChartApi | null = null;
    if (hasMacd && macdContainerRef.current) {
      macdChart = createChart(macdContainerRef.current, {
        ...commonOptions,
        width: currentWidth,
        height: 120,
        rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
      });
      const macdHist = macdChart.addSeries(HistogramSeries, { color: '#38bdf8' });
      macdHist.setData(data.filter(d => d.macd != null && d.macdSignal != null).map(d => ({ 
        time: d.time, 
        value: d.macd! - d.macdSignal!,
        color: (d.macd! - d.macdSignal!) >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(244, 63, 94, 0.6)'
      })));
      
      const macdLine = macdChart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 1.5 });
      macdLine.setData(data.filter(d => d.macd != null).map(d => ({ time: d.time, value: d.macd! })));
      
      const macdSignalLine = macdChart.addSeries(LineSeries, { color: '#fb923c', lineWidth: 1.5 });
      macdSignalLine.setData(data.filter(d => d.macdSignal != null).map(d => ({ time: d.time, value: d.macdSignal! })));
    }


    // Sync Crosshair and TimeScale
    const charts = [chart, rsiChart, macdChart].filter(Boolean) as IChartApi[];
    
    charts.forEach((c) => {
      c.subscribeCrosshairMove((param) => {
        if (!param.point || !param.time) {
          if (data.length > 0) setLegendData(data[data.length - 1]);
        } else {
          const currentData = data.find(d => d.time === param.time);
          if (currentData) setLegendData(currentData);
        }
        
        charts.forEach((otherChart) => {
          if (c !== otherChart && param.time) {
            // @ts-ignore - hack to sync crosshair position
            otherChart.setCrosshairPosition(0, param.time, candlestickSeries); 
          }
        });
      });

      // c.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      //   if (range) {
      //     charts.forEach(otherChart => {
      //       if (c !== otherChart) otherChart.timeScale().setVisibleLogicalRange(range);
      //     });
      //   }
      // });
    });

    const handleResize = () => {
      if (chartContainerRef.current && !width) {
        charts.forEach(c => {
          c.applyOptions({ width: chartContainerRef.current!.clientWidth });
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      charts.forEach(c => c.remove());
    };
  }, [data, width, height, hasRsi, hasMacd]);

  return (
    <div className="w-full relative flex flex-col gap-1 group">
      {/* Legend Overlay */}
      {legendData && (
        <div className="absolute top-2 left-2 z-10 flex flex-col gap-1 pointer-events-none bg-slate-900/60 backdrop-blur-md p-3 rounded-lg border border-slate-700/50 shadow-lg text-xs opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="flex gap-3 text-slate-300 font-mono">
            <span className="font-semibold text-slate-400">{legendData.time}</span>
            <span>O: <span className={clsx(legendData.open <= legendData.close ? 'text-emerald-400' : 'text-rose-400')}>{legendData.open.toLocaleString()}</span></span>
            <span>H: <span className={clsx(legendData.open <= legendData.close ? 'text-emerald-400' : 'text-rose-400')}>{legendData.high.toLocaleString()}</span></span>
            <span>L: <span className={clsx(legendData.open <= legendData.close ? 'text-emerald-400' : 'text-rose-400')}>{legendData.low.toLocaleString()}</span></span>
            <span>C: <span className={clsx(legendData.open <= legendData.close ? 'text-emerald-400' : 'text-rose-400')}>{legendData.close.toLocaleString()}</span></span>
            {legendData.volume != null && <span>V: <span className="text-slate-300">{(legendData.volume / 1000).toFixed(1)}k</span></span>}
          </div>
          <div className="flex gap-3 font-medium">
            {legendData.ema20 != null && <span className="text-yellow-500">EMA(20): {legendData.ema20.toFixed(2)}</span>}
            {legendData.ema50 != null && <span className="text-blue-500">EMA(50): {legendData.ema50.toFixed(2)}</span>}
            {legendData.ema200 != null && <span className="text-red-500">EMA(200): {legendData.ema200.toFixed(2)}</span>}
            {legendData.rsi != null && <span className="text-purple-400 ml-2">RSI: {legendData.rsi.toFixed(2)}</span>}
            {legendData.macd != null && <span className="text-sky-400">MACD: {legendData.macd.toFixed(2)}</span>}
          </div>
          <div className="flex gap-2 font-medium mt-1">
            {legendData.stoppingVolume && <span className="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-[10px] uppercase">Stopping Vol</span>}
            {legendData.isSpring && <span className="bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded text-[10px] uppercase">Spring</span>}
            {legendData.noDemand && <span className="bg-rose-500/20 text-rose-400 px-2 py-0.5 rounded text-[10px] uppercase">No Demand</span>}
            {legendData.climacticVolume && <span className="bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded text-[10px] uppercase">Climax</span>}
          </div>
        </div>
      )}
      <div ref={chartContainerRef} className="w-full" style={{ height: height }} />
      {hasRsi && <div ref={rsiContainerRef} className="w-full h-[120px]" />}
      {hasMacd && <div ref={macdContainerRef} className="w-full h-[120px]" />}
    </div>
  );
}
