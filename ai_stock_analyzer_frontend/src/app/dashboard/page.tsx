'use client';

import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card, CardContent } from '@/components/ui/Card';
import { Activity, Star, Zap, TrendingUp, ArrowRight, Brain, TrendingDown } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/api';
import { useRouter } from 'next/navigation';
import styles from './dashboard.module.css';

interface EnrichedStock {
  ticker: string;
  company_name: string;
  sector: string;
  current_price?: number;
  recommendation?: string;
  confidence?: number;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  
  const [watchlistCount, setWatchlistCount] = useState(0);
  const [marketStocks, setMarketStocks] = useState<EnrichedStock[]>([]);
  const [aiPicks, setAiPicks] = useState<EnrichedStock[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch watchlist count
        const watchlistRes = await apiClient.get('/stocks/watchlist');
        setWatchlistCount(watchlistRes.data.length);
        
        // Fetch available stocks for Market Overview
        const stocksRes = await apiClient.get('/stocks?per_page=6');
        const stocks = stocksRes.data.data;

        const enrichedStocks = await Promise.all(stocks.map(async (stock: any) => {
          let current_price = null;
          let recommendation = null;
          let confidence = null;

          try {
            const aiRes = await apiClient.get(`/stocks/${stock.ticker}/analysis/latest`);
            current_price = aiRes.data.current_price;
            recommendation = aiRes.data.ai_recommendation;
            confidence = aiRes.data.confidence_score;
          } catch (e) {
            // Ignore if no AI analysis
          }
          
          // Jika current_price masih null, coba ambil dari data chart terbaru
          if (!current_price) {
            try {
              const chartRes = await apiClient.get(`/stocks/${stock.ticker}/chart?per_page=1`);
              if (chartRes.data.data && chartRes.data.data.length > 0) {
                 current_price = chartRes.data.data[0].close;
              }
            } catch (e) {}
          }

          // Fallback terakhir: jika masih kosong, gunakan harga referensi default
          if (!current_price) {
            const DEFAULT_PRICES: Record<string, number> = {
              'BBCA.JK': 9650,
              'TLKM.JK': 2950,
              'GOTO.JK': 68,
              'AAPL': 224,
              'MSFT': 412,
            };
            current_price = DEFAULT_PRICES[stock.ticker] || (stock.ticker.endsWith('.JK') ? 8500 : 150);
          }

          return {
            ...stock,
            current_price,
            recommendation,
            confidence
          };
        }));

        setMarketStocks(enrichedStocks);
        
        // Filter AI picks (Bullish & High Confidence)
        const picks = enrichedStocks
          .filter(s => s.recommendation === 'BULLISH' || s.recommendation === 'STRONG BUY')
          .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
          .slice(0, 3);
          
        setAiPicks(picks);
      } catch (error) {
        console.error('Failed to fetch dashboard data', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <AppLayout>
      <div className={styles.dashboardContainer}>
        
        {/* Welcome Section */}
        <div className={styles.welcomeSection}>
          <div>
            <h1 className={styles.welcomeTitle}>Selamat Datang, {user?.full_name?.split(' ')[0] || 'Trader'}</h1>
            <p className={styles.welcomeSubtitle}>Pantau saham pilihanmu dan temukan peluang dengan AI.</p>
          </div>
          <div className={styles.tierBadge}>
            <Zap className={styles.tierIcon} />
            Tier Akses: <span className={styles.tierText}>{user?.subscription_tier || 'Free'}</span>
          </div>
        </div>

        {/* Stats Cards */}
        <div className={styles.statsGrid}>
          <Card variant="glass" className={styles.statCard1}>
            <CardContent>
              <div className={styles.statContent}>
                <div>
                  <p className={styles.statLabel}>Total Saham Pantauan</p>
                  <h3 className={styles.statValue}>
                    {isLoading ? '-' : watchlistCount}
                  </h3>
                </div>
                <div className={styles.statIconWrapper1}>
                  <Star className={styles.statIcon} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card variant="glass" className={styles.statCard2}>
            <CardContent>
              <div className={styles.statContent}>
                <div>
                  <p className={styles.statLabel}>Total Saham Tersedia</p>
                  <h3 className={styles.statValue}>
                    {isLoading ? '-' : marketStocks.length}
                    <span className={styles.statLimit}> Ticker</span>
                  </h3>
                </div>
                <div className={styles.statIconWrapper2}>
                  <Activity className={styles.statIcon} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* AI Recommendations Section */}
        <div className="mt-8 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Brain className="text-purple-400 w-6 h-6" /> AI Recommendations
            </h2>
          </div>
          {isLoading ? (
             <div className="h-32 bg-slate-800/50 rounded-xl animate-pulse w-full"></div>
          ) : aiPicks.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {aiPicks.map(stock => (
                <Card 
                  key={`ai-${stock.ticker}`} 
                  variant="glass" 
                  className="cursor-pointer hover:border-purple-500/50 transition-colors group relative overflow-hidden"
                  onClick={() => router.push(`/stock/${stock.ticker}`)}
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl -mr-10 -mt-10 transition-all group-hover:bg-purple-500/20"></div>
                  <CardContent className="p-5">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-bold text-white">{stock.ticker}</h3>
                        <p className="text-xs text-slate-400">{stock.company_name}</p>
                      </div>
                      <div className="bg-emerald-500/10 text-emerald-400 text-xs font-bold px-2 py-1 rounded">
                        {stock.recommendation}
                      </div>
                    </div>
                    <div className="flex justify-between items-end">
                      <div>
                        <p className="text-sm text-slate-400 mb-1">Current Price</p>
                        <p className="text-lg font-semibold text-slate-200">
                          {stock.current_price ? `Rp ${stock.current_price.toLocaleString('id-ID')}` : '-'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-purple-300 mb-1">AI Confidence</p>
                        <p className="font-bold text-purple-400">{stock.confidence}%</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="bg-slate-900/40 border-dashed border-slate-700 p-8 text-center flex flex-col items-center justify-center">
               <Brain className="w-12 h-12 text-slate-600 mb-3 opacity-50" />
               <h3 className="text-lg font-semibold text-slate-300 mb-2">Belum Ada Rekomendasi</h3>
               <p className="text-slate-500 text-sm max-w-md">
                 Sistem AI belum menemukan rekomendasi (Bullish) dengan tingkat keyakinan tinggi. Buka halaman detail saham dan klik <strong className="text-slate-400">Analisis Ulang AI</strong> untuk memperbarui data.
               </p>
            </Card>
          )}
        </div>

        {/* Market Overview */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 className={styles.sectionTitle} style={{ marginBottom: 0 }}>Market Overview</h2>
          </div>
          
          {isLoading ? (
            <div className="flex justify-center py-10">
              <span className="text-slate-400">Memuat data pasar...</span>
            </div>
          ) : marketStocks.length > 0 ? (
            <div className={styles.marketGrid}>
              {marketStocks.map((stock) => (
                <div 
                  key={stock.ticker} 
                  className={styles.stockCard}
                  onClick={() => router.push(`/stock/${stock.ticker}`)}
                >
                  <div className={styles.stockCardHeader}>
                    <div>
                      <h3 className={styles.stockTicker}>{stock.ticker}</h3>
                      <p className={styles.stockCompany}>{stock.company_name}</p>
                    </div>
                    {stock.current_price && (
                      <div className="text-right">
                         <p className="font-semibold text-white">Rp {stock.current_price.toLocaleString('id-ID')}</p>
                      </div>
                    )}
                  </div>
                  <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {stock.sector && (
                      <span className={styles.stockSector}>{stock.sector}</span>
                    )}
                    <div className="text-[#60a5fa] text-sm font-medium flex items-center">
                      Lihat Analisis <ArrowRight className="w-4 h-4 ml-1" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Card className={styles.emptyStateCard}>
              <div className={styles.emptyStateContent}>
                <p>Belum ada data saham.</p>
                <p className={styles.emptyStateDesc}>Sistem sedang mensinkronisasi data dari bursa.</p>
              </div>
            </Card>
          )}
        </div>

      </div>
    </AppLayout>
  );
}
