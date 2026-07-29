'use client';

import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card, CardContent } from '@/components/ui/Card';
import { Activity, Star, Zap, TrendingUp, ArrowRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/api';
import { useRouter } from 'next/navigation';
import styles from './dashboard.module.css';

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  
  const [watchlistCount, setWatchlistCount] = useState(0);
  const [marketStocks, setMarketStocks] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch watchlist count
        const watchlistRes = await apiClient.get('/stocks/watchlist');
        setWatchlistCount(watchlistRes.data.length);
        
        // Fetch available stocks for Market Overview
        const stocksRes = await apiClient.get('/stocks?per_page=12');
        setMarketStocks(stocksRes.data.data);
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
                    {stock.sector && (
                      <span className={styles.stockSector}>{stock.sector}</span>
                    )}
                  </div>
                  <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', color: '#60a5fa', fontSize: '0.875rem', fontWeight: 500 }}>
                    Lihat Analisis AI <ArrowRight className="w-4 h-4 ml-1" />
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
