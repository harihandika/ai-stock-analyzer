'use client';

import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Activity, Star, Zap } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import styles from './dashboard.module.css';
import clsx from 'clsx';

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ watchlistCount: 0, analysisCount: 0 });

  useEffect(() => {
    // Fetch dashboard stats (mocking for now, can implement actual endpoints later)
    setStats({
      watchlistCount: 5,
      analysisCount: 12
    });
  }, []);

  return (
    <AppLayout>
      <div className={styles.dashboardContainer}>
        
        {/* Welcome Section */}
        <div className={styles.welcomeSection}>
          <div>
            <h1 className={styles.welcomeTitle}>Selamat Datang, {user?.full_name?.split(' ')[0] || 'Trader'}</h1>
            <p className={styles.welcomeSubtitle}>Ini adalah ringkasan portofolio dan status pasar hari ini.</p>
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
                  <h3 className={styles.statValue}>{stats.watchlistCount}</h3>
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
                  <p className={styles.statLabel}>Analisis AI Bulan Ini</p>
                  <h3 className={styles.statValue}>
                    {stats.analysisCount} <span className={styles.statLimit}>/ {user?.subscription_tier === 'premium' ? '∞' : '3'}</span>
                  </h3>
                </div>
                <div className={styles.statIconWrapper2}>
                  <Activity className={styles.statIcon} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions / Market Overview */}
        <div>
          <h2 className={styles.sectionTitle}>Aktivitas Terakhir</h2>
          <Card className={styles.emptyStateCard}>
            <div className={styles.emptyStateContent}>
              <p>Belum ada riwayat aktivitas analisis.</p>
              <p className={styles.emptyStateDesc}>Cari saham di kotak pencarian atas untuk memulai analisis cerdas.</p>
            </div>
          </Card>
        </div>

      </div>
    </AppLayout>
  );
}
