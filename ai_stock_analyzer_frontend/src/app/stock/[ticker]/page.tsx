'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { AppLayout } from '@/components/layout/AppLayout';
import { AIReportCard } from '@/components/stock/AIReportCard';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Star, RefreshCw, AlertTriangle, TrendingUp, TrendingDown, Play } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/services/api';
import clsx from 'clsx';

// Load chart only on client side to avoid SSR issues with canvas
const StockChart = dynamic(
  () => import('@/components/charts/StockChart').then(mod => mod.StockChart),
  { ssr: false, loading: () => <div className="h-[400px] flex items-center justify-center text-slate-500 animate-pulse">Memuat Grafik Real-time...</div> }
);

export default function StockDetailPage() {
  const params = useParams();
  const router = useRouter();
  const ticker = params.ticker as string;
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isAddingWatchlist, setIsAddingWatchlist] = useState(false);
  
  const [chartData, setChartData] = useState<any[]>([]);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [stockInfo, setStockInfo] = useState({ companyName: 'Perusahaan Publik Tbk.' });
  const [activeTimeframe, setActiveTimeframe] = useState('1Y');

  // Derived styling helpers
  const isJK = ticker.endsWith('.JK');
  const exchangeTag = isJK ? 'IHSG' : 'NASDAQ / NYSE';
  const currencySymbol = isJK ? 'Rp' : '$';

  const fetchData = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Chart Data
      const chartRes = await apiClient.get(`/stocks/${ticker}/chart?per_page=100`);
      if (chartRes.data && chartRes.data.data && chartRes.data.data.length > 0) {
        const formattedChart = chartRes.data.data.map((p: any) => ({
          time: p.trading_date,
          open: p.open,
          high: p.high,
          low: p.low,
          close: p.close
        }));
        setChartData(formattedChart);
      } else {
        throw new Error("No chart data");
      }

      // 2. Fetch AI Analysis
      try {
        const aiRes = await apiClient.get(`/stocks/${ticker}/analysis/latest`);
        setAiAnalysis(aiRes.data);
        if (aiRes.data.company_name) {
          setStockInfo({ companyName: aiRes.data.company_name });
        }
      } catch (err: any) {
        throw new Error("No AI data");
      }
    } catch (error) {
      console.log("Menggunakan mock data untuk demonstrasi UI karena API gagal...");
      
      // Fallback Mock Data for UI Demonstration
      let mockChart = [];
      let time = new Date().getTime() - 100 * 24 * 60 * 60 * 1000;
      let lastClose = isJK ? 10000 : 150;
      for (let i = 0; i < 100; i++) {
        const dateStr = new Date(time).toISOString().split('T')[0];
        const open = lastClose + (Math.random() - 0.5) * (isJK ? 200 : 5);
        const high = open + Math.random() * (isJK ? 200 : 5);
        const low = open - Math.random() * (isJK ? 200 : 5);
        const close = (open + high + low) / 3 + (Math.random() - 0.5) * (isJK ? 100 : 2);
        mockChart.push({ time: dateStr, open, high, low, close });
        lastClose = close;
        time += 24 * 60 * 60 * 1000;
      }
      setChartData(mockChart);

      setAiAnalysis({
        current_price: lastClose,
        ai_recommendation: 'BULLISH',
        confidence_score: 88,
        wyckoff_phase: 'Phase C',
        ai_summary: `[MOCK DATA] Saham ${ticker} saat ini berada di area support kuat dengan akumulasi institusi yang masif. Secara fundamental, pertumbuhan EPS melampaui estimasi Wall Street selama 3 kuartal berturut-turut. Kami merekomendasikan posisi beli agresif dengan stop loss ketat di bawah area konsolidasi.`,
        vpa_insight: 'Strong buying pressure detected on low timeframe',
        technical_indicators: {
          rsi_14: 65.4,
          macd: 2.15,
          climactic_volume: true
        }
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (ticker) {
      fetchData();
    }
  }, [ticker]);

  const handleSyncData = async () => {
    setIsSyncing(true);
    try {
      await apiClient.post(`/stocks/${ticker}/sync`);
      await fetchData(); // re-fetch after sync
    } catch (error) {
      console.error("Gagal sinkronisasi data", error);
      alert("Gagal melakukan analisis ulang. Silakan coba lagi nanti.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleAddWatchlist = async () => {
    setIsAddingWatchlist(true);
    try {
      await apiClient.post('/stocks/watchlist', {
        ticker: ticker,
        notes: 'Added from stock detail page'
      });
      alert('Berhasil ditambahkan ke Watchlist!');
    } catch (error: any) {
      if (error.response?.status === 409) {
        alert('Saham ini sudah ada di Watchlist Anda.');
      } else {
        alert('Gagal menambahkan ke Watchlist.');
      }
    } finally {
      setIsAddingWatchlist(false);
    }
  };

  // Mock calculation for today's change if real chart data exists
  const currentPrice = aiAnalysis?.current_price || (chartData.length > 0 ? chartData[chartData.length - 1].close : 0);
  const previousPrice = chartData.length > 1 ? chartData[chartData.length - 2].close : currentPrice;
  const priceChange = currentPrice - previousPrice;
  const percentChange = previousPrice ? (priceChange / previousPrice) * 100 : 0;
  const isPositive = priceChange >= 0;

  return (
    <AppLayout>
      {/* Ambient Background Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/10 via-[#0a0b10] to-emerald-900/5 -z-10" />

      <div className="max-w-7xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 fade-in duration-700 pb-12">
        
        {/* Header Section */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6 border-b border-[rgba(255,255,255,0.08)] pb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
            <div>
              <div className="flex items-center space-x-3 mb-1">
                <h1 className="text-5xl font-extrabold tracking-tight text-white drop-shadow-md">{ticker}</h1>
                <span className="px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/50 text-xs font-bold text-slate-300 tracking-wider">
                  {exchangeTag}
                </span>
              </div>
              <p className="text-slate-400 text-lg font-medium">{stockInfo.companyName}</p>
            </div>

            {/* Price Block */}
            {currentPrice > 0 && (
              <div className="sm:border-l sm:border-[rgba(255,255,255,0.1)] sm:pl-6 sm:ml-2">
                <div className="flex items-baseline space-x-2">
                  <span className="text-slate-400 font-medium">{currencySymbol}</span>
                  <span className="text-4xl font-bold text-white tracking-tight">{currentPrice.toLocaleString('id-ID')}</span>
                </div>
                <div className={clsx(
                  "flex items-center mt-1 font-semibold",
                  isPositive ? "text-emerald-400" : "text-rose-400"
                )}>
                  {isPositive ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                  <span>{isPositive ? '+' : ''}{priceChange.toLocaleString('id-ID')} ({isPositive ? '+' : ''}{percentChange.toFixed(2)}%)</span>
                  <span className="text-slate-500 text-xs ml-2 font-normal">Hari Ini</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            <Link href={`/stock/${ticker}/backtest`} className="flex-1 lg:flex-none">
              <Button variant="outline" className="w-full border-slate-700 hover:bg-slate-800 text-indigo-400 border-indigo-500/50 hover:text-indigo-300 transition-all shadow-sm">
                <Play className="w-4 h-4 mr-2" /> Backtest
              </Button>
            </Link>
            <Button 
              onClick={handleAddWatchlist} 
              isLoading={isAddingWatchlist} 
              variant="outline" 
              className="flex-1 lg:flex-none border-slate-700 hover:bg-slate-800 hover:text-white hover:border-slate-600 transition-all shadow-sm"
            >
              <Star className="w-4 h-4 mr-2" /> Tambah Watchlist
            </Button>
            <Button 
              onClick={handleSyncData} 
              isLoading={isSyncing} 
              className="flex-1 lg:flex-none bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_25px_rgba(79,70,229,0.5)] transition-all border-none"
            >
              <RefreshCw className={clsx("w-4 h-4 mr-2", isSyncing && "animate-spin")} /> 
              {chartData.length > 0 ? 'Analisis Ulang AI' : 'Mulai Analisis AI'}
            </Button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          
          {/* Left Column: Chart & Indicators */}
          <div className="xl:col-span-2 space-y-8">
            <Card variant="glass" className="p-1 border border-slate-800/50 shadow-2xl bg-black/20 backdrop-blur-xl">
              <div className="p-5 border-b border-slate-800/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <h3 className="text-lg font-bold text-white tracking-wide">Grafik Pergerakan Historis</h3>
                <div className="flex bg-slate-900/50 p-1 rounded-lg border border-slate-800">
                  {['1W', '1M', '3M', '6M', '1Y'].map(tf => (
                    <button 
                      key={tf} 
                      onClick={() => setActiveTimeframe(tf)}
                      className={clsx(
                        "px-4 py-1.5 text-xs font-semibold rounded-md transition-all duration-200",
                        activeTimeframe === tf 
                          ? "bg-indigo-500/20 text-indigo-300 shadow-sm" 
                          : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                      )}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
              <div className="p-5">
                {isLoading ? (
                  <div className="h-[450px] flex items-center justify-center text-slate-500 animate-pulse">Mensinkronisasi Data Pasar...</div>
                ) : chartData.length > 0 ? (
                  <div className="h-[450px]">
                    <StockChart data={chartData} />
                  </div>
                ) : (
                  <div className="h-[450px] flex flex-col items-center justify-center text-slate-400 bg-slate-900/20 rounded-lg border border-dashed border-slate-800">
                    <AlertTriangle className="w-16 h-16 mb-4 text-slate-600 opacity-50" />
                    <p className="text-lg mb-1 text-slate-300">Data historis belum tersedia</p>
                    <p className="text-sm mb-6 text-slate-500">Silakan tarik data terbaru dari bursa untuk memulai.</p>
                    <Button onClick={handleSyncData} isLoading={isSyncing} className="bg-slate-800 hover:bg-slate-700">
                      Tarik Data Sekarang
                    </Button>
                  </div>
                )}
              </div>
            </Card>
            
            {/* Advanced Indicators */}
            {aiAnalysis && aiAnalysis.technical_indicators && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* RSI Card */}
                <Card variant="glass" className="p-5 border-slate-800/50 hover:border-slate-700 transition-colors bg-gradient-to-b from-slate-900/40 to-transparent">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2 block">RSI (14)</span>
                  <span className={clsx(
                    "text-2xl font-mono font-bold drop-shadow-sm",
                    aiAnalysis.technical_indicators.rsi_14 > 70 ? "text-rose-400" :
                    aiAnalysis.technical_indicators.rsi_14 < 30 ? "text-emerald-400" :
                    "text-white"
                  )}>
                    {aiAnalysis.technical_indicators.rsi_14 ? aiAnalysis.technical_indicators.rsi_14.toFixed(2) : '-'}
                  </span>
                  <p className="text-xs text-slate-500 mt-2">
                    {aiAnalysis.technical_indicators.rsi_14 > 70 ? "Kondisi Overbought" :
                     aiAnalysis.technical_indicators.rsi_14 < 30 ? "Kondisi Oversold" :
                     "Momentum Netral"}
                  </p>
                </Card>

                {/* MACD Card */}
                <Card variant="glass" className="p-5 border-slate-800/50 hover:border-slate-700 transition-colors bg-gradient-to-b from-slate-900/40 to-transparent">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2 block">MACD</span>
                  <span className={clsx(
                    "text-2xl font-mono font-bold drop-shadow-sm",
                    aiAnalysis.technical_indicators.macd > 0 ? "text-emerald-400" : "text-rose-400"
                  )}>
                    {aiAnalysis.technical_indicators.macd ? (aiAnalysis.technical_indicators.macd > 0 ? '+' : '') + aiAnalysis.technical_indicators.macd.toFixed(2) : '-'}
                  </span>
                  <p className="text-xs text-slate-500 mt-2">
                    {aiAnalysis.technical_indicators.macd > 0 ? "Trend Bullish" : "Trend Bearish"}
                  </p>
                </Card>

                {/* VPA Card */}
                <Card variant="glass" className="p-5 border-slate-800/50 hover:border-slate-700 transition-colors bg-gradient-to-b from-slate-900/40 to-transparent">
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2 block">Volume (VPA)</span>
                  <span className={clsx(
                    "text-xl font-bold drop-shadow-sm",
                    aiAnalysis.technical_indicators.climactic_volume ? "text-amber-400" : "text-emerald-400"
                  )}>
                    {aiAnalysis.technical_indicators.climactic_volume ? 'Climactic Anomaly' : 'Normal / Stabil'}
                  </span>
                  <p className="text-xs text-slate-500 mt-2">
                    Analisis Volume Spread
                  </p>
                </Card>

                {/* Wyckoff Card */}
                <Card variant="glass" className="p-5 border-slate-800/50 hover:border-slate-700 transition-colors bg-gradient-to-b from-slate-900/40 to-transparent relative overflow-hidden">
                  <div className="absolute -right-4 -bottom-4 w-16 h-16 bg-indigo-500/10 rounded-full blur-xl" />
                  <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2 block">Wyckoff Phase</span>
                  <span className="text-xl font-bold text-indigo-300 drop-shadow-sm">
                    {aiAnalysis.wyckoff_phase || 'Phase B'}
                  </span>
                  <p className="text-xs text-slate-500 mt-2">
                    Pola Distribusi & Akumulasi
                  </p>
                </Card>
              </div>
            )}
          </div>

          {/* Right Column: AI Report */}
          <div className="xl:col-span-1">
            {aiAnalysis ? (
              <div className="sticky top-24">
                <AIReportCard
                  ticker={ticker}
                  summary={aiAnalysis.ai_summary || aiAnalysis.vpa_insight || 'Analisis AI belum memiliki rangkuman teks.'}
                  sentiment={aiAnalysis.ai_recommendation || 'NEUTRAL'}
                  targetPrice={aiAnalysis.current_price * 1.05} // Evaluated dummy target price
                  confidenceScore={aiAnalysis.confidence_score || 70}
                  riskLevel="MEDIUM"
                />
              </div>
            ) : (
              <Card variant="glass" className="h-[600px] flex flex-col items-center justify-center p-10 text-center border-slate-800/50 bg-slate-900/20">
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-indigo-500/20 rounded-full blur-xl animate-pulse" />
                  <div className="w-20 h-20 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center relative z-10 shadow-xl">
                    <Star className="w-10 h-10 text-slate-400" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-white mb-3">Belum Ada Analisis</h3>
                <p className="text-base text-slate-400 mb-8 leading-relaxed max-w-xs mx-auto">
                  Sistem AI kami belum memproses pergerakan teknikal dan fundamental untuk saham ini.
                </p>
                <Button onClick={handleSyncData} isLoading={isSyncing} className="w-full bg-indigo-600 hover:bg-indigo-500 text-lg py-6 shadow-[0_0_20px_rgba(79,70,229,0.2)]">
                  <RefreshCw className="w-5 h-5 mr-3" /> Mulai Analisis AI
                </Button>
              </Card>
            )}
          </div>
        </div>
        
      </div>
    </AppLayout>
  );
}
