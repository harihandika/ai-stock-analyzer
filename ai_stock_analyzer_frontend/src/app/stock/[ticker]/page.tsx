'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { AppLayout } from '@/components/layout/AppLayout';
import { AIReportCard } from '@/components/stock/AIReportCard';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Star, RefreshCw } from 'lucide-react';
import { useParams } from 'next/navigation';

// Load chart only on client side to avoid SSR issues with canvas
const StockChart = dynamic(
  () => import('@/components/charts/StockChart').then(mod => mod.StockChart),
  { ssr: false, loading: () => <div className="h-[400px] flex items-center justify-center text-slate-500">Memuat Grafik...</div> }
);

export default function StockDetailPage() {
  const params = useParams();
  const ticker = params.ticker as string;
  
  const [isLoading, setIsLoading] = useState(false);
  const [chartData, setChartData] = useState<any[]>([]);

  useEffect(() => {
    // Mock fetch chart data
    const generateMockData = () => {
      let data = [];
      let time = new Date('2026-01-01').getTime();
      let lastClose = 10000;
      
      for (let i = 0; i < 60; i++) {
        const dateObj = new Date(time);
        const dateStr = dateObj.toISOString().split('T')[0];
        
        const open = lastClose + (Math.random() - 0.5) * 200;
        const high = open + Math.random() * 200;
        const low = open - Math.random() * 200;
        const close = (open + high + low) / 3 + (Math.random() - 0.5) * 100;
        
        data.push({ time: dateStr, open, high, low, close });
        
        lastClose = close;
        time += 24 * 60 * 60 * 1000;
      }
      return data;
    };
    
    setChartData(generateMockData());
  }, [ticker]);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6 animate-fade-in pb-10">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[rgba(255,255,255,0.08)] pb-6">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-4xl font-bold tracking-tight">{ticker}</h1>
              <span className="px-3 py-1 rounded bg-slate-800 text-xs font-semibold text-slate-300">IHSG</span>
            </div>
            <p className="text-slate-400 mt-2 text-lg">Perusahaan Publik Tbk.</p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="ghost" className="text-slate-300">
              <Star className="w-5 h-5 mr-2" /> Tambah Watchlist
            </Button>
            <Button onClick={() => setIsLoading(true)} isLoading={isLoading} className="shadow-[0_0_15px_rgba(59,130,246,0.3)]">
              <RefreshCw className="w-4 h-4 mr-2" /> Analisis Ulang AI
            </Button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Chart */}
          <div className="lg:col-span-2 space-y-6">
            <Card variant="glass" className="p-1">
              <div className="p-4 border-b border-[rgba(255,255,255,0.05)] flex items-center justify-between">
                <h3 className="font-semibold text-white">Grafik Harga Historis</h3>
                <div className="flex space-x-2">
                  {['1W', '1M', '3M', '6M', '1Y'].map(tf => (
                    <button key={tf} className="px-2 py-1 text-xs rounded hover:bg-[rgba(255,255,255,0.1)] text-slate-400 hover:text-white transition-colors">
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
              <div className="p-4">
                {chartData.length > 0 && <StockChart data={chartData} />}
              </div>
            </Card>
          </div>

          {/* Right Column: AI Report */}
          <div className="lg:col-span-1">
            <AIReportCard
              summary={`Berdasarkan pola historis dan sentimen pasar makro terbaru, ${ticker} menunjukkan tanda-tanda akumulasi yang kuat di level support saat ini. Laporan keuangan kuartal terakhir melampaui ekspektasi konsensus sebesar 12%. Probabilitas breakout resistensi jangka pendek dinilai cukup tinggi.`}
              sentiment="BULLISH"
              targetPrice={12500}
              confidenceScore={87}
              riskLevel="LOW"
            />
          </div>
        </div>
        
      </div>
    </AppLayout>
  );
}
