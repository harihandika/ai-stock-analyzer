'use client';

import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Activity, Star, Zap } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/api';
import Link from 'next/link';

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
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        
        {/* Welcome Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Selamat Datang, {user?.full_name?.split(' ')[0] || 'Trader'}</h1>
            <p className="text-slate-400 mt-1">Ini adalah ringkasan portofolio dan status pasar hari ini.</p>
          </div>
          <div className="px-4 py-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-medium text-sm flex items-center">
            <Zap className="w-4 h-4 mr-2" />
            Tier Akses: <span className="capitalize ml-1 text-white">{user?.subscription_tier || 'Free'}</span>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card variant="glass" className="border-t-4 border-t-blue-500">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-400">Total Saham Pantauan</p>
                  <h3 className="text-3xl font-bold mt-2">{stats.watchlistCount}</h3>
                </div>
                <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
                  <Star className="w-6 h-6 text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card variant="glass" className="border-t-4 border-t-indigo-500">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-400">Analisis AI Bulan Ini</p>
                  <h3 className="text-3xl font-bold mt-2">{stats.analysisCount} <span className="text-sm text-slate-500 font-normal">/ {user?.subscription_tier === 'premium' ? '∞' : '3'}</span></h3>
                </div>
                <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center">
                  <Activity className="w-6 h-6 text-indigo-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions / Market Overview */}
        <div>
          <h2 className="text-xl font-bold mb-4">Aktivitas Terakhir</h2>
          <Card className="bg-[#12141d]/50 border-[rgba(255,255,255,0.05)]">
            <div className="p-8 text-center text-slate-500">
              <p>Belum ada riwayat aktivitas analisis.</p>
              <p className="text-sm mt-2">Cari saham di kotak pencarian atas untuk memulai analisis cerdas.</p>
            </div>
          </Card>
        </div>

      </div>
    </AppLayout>
  );
}
