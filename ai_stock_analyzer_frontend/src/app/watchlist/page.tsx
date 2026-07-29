'use client';

import React from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card, CardContent } from '@/components/ui/Card';
import { Star, TrendingUp, TrendingDown } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import styles from './watchlist.module.css';

export default function WatchlistPage() {
  // Mock data for now
  const watchlist = [
    { ticker: 'BBCA.JK', name: 'Bank Central Asia Tbk', price: 9850, change: 1.5, bullish: true },
    { ticker: 'TLKM.JK', name: 'Telkom Indonesia Tbk', price: 3800, change: -0.8, bullish: false },
    { ticker: 'GOTO.JK', name: 'GoTo Gojek Tokopedia', price: 85, change: 4.2, bullish: true },
  ];

  return (
    <AppLayout>
      <div className={styles.container}>
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>Watchlist Saham</h1>
            <p className={styles.subtitle}>Pantau pergerakan saham favorit Anda.</p>
          </div>
          <Button variant="secondary">
            + Tambah Ticker
          </Button>
        </div>

        <div className={styles.list}>
          {watchlist.map((stock) => (
            <Card key={stock.ticker} className={styles.cardItem}>
              <Link href={`/stock/${stock.ticker}`}>
                <div className={styles.cardContent}>
                  <div className={styles.leftInfo}>
                    <div className={styles.starWrapper}>
                      <Star className={styles.starIcon} />
                    </div>
                    <div>
                      <h3 className={styles.ticker}>{stock.ticker}</h3>
                      <p className={styles.name}>{stock.name}</p>
                    </div>
                  </div>

                  <div className={styles.rightInfo}>
                    <p className={styles.price}>Rp {stock.price.toLocaleString('id-ID')}</p>
                    <p className={`${styles.change} ${stock.bullish ? styles.bullish : styles.bearish}`}>
                      {stock.bullish ? <TrendingUp className={styles.changeIcon} /> : <TrendingDown className={styles.changeIcon} />}
                      {stock.bullish ? '+' : ''}{stock.change}%
                    </p>
                  </div>
                </div>
              </Link>
            </Card>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
