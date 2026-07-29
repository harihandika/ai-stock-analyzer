'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LayoutDashboard, LineChart, Star, Settings, LogOut, Search, Bell, User as UserIcon, Moon } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';
import { apiClient } from '@/services/api';
import styles from './layout.module.css';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated, isLoading, logout, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  
  // States
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const searchRef = useRef<HTMLFormElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);
  const notificationsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setIsSettingsOpen(false);
      }
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setIsNotificationsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Search Debounce
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchQuery.trim().length >= 2) {
        setIsSearching(true);
        try {
          const res = await apiClient.get(`/stocks?q=${searchQuery}&per_page=5`);
          setSearchResults(res.data.data);
          setIsSearchOpen(true);
        } catch (error) {
          console.error(error);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
        setIsSearchOpen(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  if (isLoading || !isAuthenticated) {
    return <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>;
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setIsSearchOpen(false);
      router.push(`/stock/${searchQuery.toUpperCase()}`);
    }
  };

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Watchlist', href: '/watchlist', icon: Star },
    { name: 'Settings', href: '/settings', icon: Settings },
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
          <form ref={searchRef} onSubmit={handleSearch} className={styles.searchForm}>
            <Search className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Cari Ticker atau Nama Perusahaan..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => {
                if (searchResults.length > 0) setIsSearchOpen(true);
              }}
              className={styles.searchInput}
            />
            {isSearchOpen && (
              <div className={clsx(styles.dropdown, styles.searchDropdown)}>
                {isSearching ? (
                  <div className={styles.dropdownItem} style={{ justifyContent: 'center' }}>Mencari...</div>
                ) : searchResults.length > 0 ? (
                  searchResults.map(stock => (
                    <button
                      key={stock.ticker}
                      type="button"
                      className={styles.dropdownItem}
                      onClick={() => {
                        setIsSearchOpen(false);
                        setSearchQuery('');
                        router.push(`/stock/${stock.ticker}`);
                      }}
                    >
                      <span style={{ fontWeight: 'bold' }}>{stock.ticker}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{stock.company_name}</span>
                    </button>
                  ))
                ) : (
                  <div className={styles.dropdownItem} style={{ justifyContent: 'center' }}>Saham tidak ditemukan</div>
                )}
              </div>
            )}
          </form>

          <div className={styles.headerActions}>
            <div ref={notificationsRef} style={{ position: 'relative' }}>
              <button 
                className={styles.actionBtn}
                onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              >
                <Bell width={20} height={20} />
                <span className={styles.notificationBadge}></span>
              </button>
              {isNotificationsOpen && (
                <div className={styles.dropdown} style={{ minWidth: '250px' }}>
                  <div className={styles.dropdownHeader}>Notifications</div>
                  <div className={styles.dropdownItem} style={{ justifyContent: 'center', padding: '20px 16px', color: 'var(--text-muted)' }}>
                    Belum ada notifikasi baru
                  </div>
                </div>
              )}
            </div>

            <div ref={settingsRef} style={{ position: 'relative' }}>
              <button 
                className={styles.actionBtn}
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              >
                <Settings width={20} height={20} />
              </button>
              {isSettingsOpen && (
                <div className={styles.dropdown}>
                  <div className={styles.dropdownHeader}>Akun Saya</div>
                  <Link href="/settings" className={styles.dropdownItem} onClick={() => setIsSettingsOpen(false)}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><UserIcon size={16} /> Profil</span>
                  </Link>
                  <button className={styles.dropdownItem}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Moon size={16} /> Tema Gelap</span>
                  </button>
                  <div style={{ height: '1px', background: 'var(--glass-border)', margin: '4px 0' }}></div>
                  <button onClick={logout} className={styles.dropdownItem} style={{ color: '#fb7185' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><LogOut size={16} /> Sign Out</span>
                  </button>
                </div>
              )}
            </div>
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
