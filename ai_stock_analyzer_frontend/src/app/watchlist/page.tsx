'use client';

import React from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card, CardContent } from '@/components/ui/Card';
import { Star, TrendingUp, TrendingDown } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';

export default function WatchlistPage() {
  // Mock data for now
  const watchlist = [
    { ticker: 'BBCA.JK', name: 'Bank Central Asia Tbk', price: 9850, change: 1.5, bullish: true },
    { ticker: 'TLKM.JK', name: 'Telkom Indonesia Tbk', price: 3800, change: -0.8, bullish: false },
    { ticker: 'GOTO.JK', name: 'GoTo Gojek Tokopedia', price: 85, change: 4.2, bullish: true },
  ];

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto animate-fade-in">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Watchlist Saham</h1>
            <p className="text-slate-400 mt-1">Pantau pergerakan saham favorit Anda.</p>
          </div>
          <Button variant="secondary">
            + Tambah Ticker
          </Button>
        </div>

        <div className="space-y-4">
          {watchlist.map((stock) => (
            <Card key={stock.ticker} className="hover:border-[rgba(255,255,255,0.2)] transition-colors group cursor-pointer">
              <Link href={`/stock/${stock.ticker}`}>
                <CardContent className="p-4 sm:p-6 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center flex-shrink-0">
                      <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-white group-hover:text-blue-400 transition-colors">{stock.ticker}</h3>
                      <p className="text-sm text-slate-400">{stock.name}</p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="font-mono text-lg font-bold">Rp {stock.price.toLocaleString('id-ID')}</p>
                    <p className={`flex items-center justify-end text-sm font-medium mt-1 ${stock.bullish ? 'text-bullish' : 'text-bearish'}`}>
                      {stock.bullish ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                      {stock.bullish ? '+' : ''}{stock.change}%
                    </p>
                  </div>
                </CardContent>
              </Link>
            </Card>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
