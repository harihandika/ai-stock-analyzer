'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LayoutDashboard, LineChart, Star, Settings, LogOut, Search, Bell } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';
import { Input } from '../ui/Input';
import styles from './layout.module.css';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated, isLoading, logout, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>;
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/stock/${searchQuery.toUpperCase()}`);
    }
  };

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Watchlist', href: '/watchlist', icon: Star },
  ];

  return (
    <div className={styles.layoutContainer}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logoIcon}>
            <LineChart width={20} height={20} color="#60a5fa" />
          </div>
          <span className={styles.logoText}>AI Analyzer</span>
        </div>

        <nav className={styles.nav}>
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link key={item.name} href={item.href}>
                <span className={clsx(styles.navItem, isActive && styles.navItemActive)}>
                  <item.icon className={styles.navIcon} />
                  {item.name}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <div className={styles.userAvatar}>
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className={styles.userDetails}>
              <p className={styles.userName}>{user?.full_name}</p>
              <p className={styles.userTier}>{user?.subscription_tier} Tier</p>
            </div>
          </div>
          <button onClick={logout} className={styles.signOutBtn}>
            <LogOut width={16} height={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className={styles.mainContent}>
        {/* Top Header */}
        <header className={styles.topHeader}>
          <form onSubmit={handleSearch} className={styles.searchForm}>
            <Search className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Cari Ticker (ex: BBCA.JK)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </form>

          <div className={styles.headerActions}>
            <button className={styles.actionBtn}>
              <Bell width={20} height={20} />
              <span className={styles.notificationBadge}></span>
            </button>
            <button className={styles.actionBtn}>
              <Settings width={20} height={20} />
            </button>
          </div>
        </header>

        {/* Scrollable Page Content */}
        <div className={styles.pageContent}>
          {children}
        </div>
      </main>
    </div>
  );
}
