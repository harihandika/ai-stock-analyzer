'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LayoutDashboard, LineChart, Star, Settings, LogOut, Search, Bell } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';
import { Input } from '../ui/Input';

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
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
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
    <div className="flex h-screen overflow-hidden bg-[#0a0b10]">
      {/* Sidebar */}
      <aside className="w-[260px] flex-shrink-0 border-r border-[rgba(255,255,255,0.08)] bg-[#12141d]/80 backdrop-blur-xl flex flex-col">
        <div className="h-20 flex items-center px-6 border-b border-[rgba(255,255,255,0.08)]">
          <div className="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center mr-3">
            <LineChart className="w-5 h-5 text-blue-400" />
          </div>
          <span className="font-bold text-lg tracking-tight">AI Analyzer</span>
        </div>

        <nav className="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link key={item.name} href={item.href}>
                <span className={clsx(
                  'flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive 
                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-[0_0_10px_rgba(59,130,246,0.1)]' 
                    : 'text-slate-400 hover:text-white hover:bg-[rgba(255,255,255,0.05)]'
                )}>
                  <item.icon className={clsx('w-5 h-5 mr-3', isActive ? 'text-blue-400' : 'text-slate-500')} />
                  {item.name}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-[rgba(255,255,255,0.08)]">
          <div className="flex items-center mb-4 px-2">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold uppercase text-xs">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="ml-3 overflow-hidden">
              <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
              <p className="text-xs text-slate-500 truncate capitalize">{user?.subscription_tier} Tier</p>
            </div>
          </div>
          <button 
            onClick={logout}
            className="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium text-rose-400 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4 mr-3" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Top Header */}
        <header className="h-20 flex-shrink-0 flex items-center justify-between px-8 border-b border-[rgba(255,255,255,0.08)] bg-[#0a0b10]/80 backdrop-blur-md z-10">
          <form onSubmit={handleSearch} className="w-96 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Cari Ticker (ex: BBCA.JK)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#12141d] border border-[rgba(255,255,255,0.08)] rounded-full py-2 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
          </form>

          <div className="flex items-center space-x-4">
            <button className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-[rgba(255,255,255,0.05)] text-slate-400 transition-colors relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full shadow-[0_0_5px_#f43f5e]"></span>
            </button>
            <button className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-[rgba(255,255,255,0.05)] text-slate-400 transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Scrollable Page Content */}
        <div className="flex-1 overflow-auto p-8 relative">
          {children}
        </div>
      </main>
    </div>
  );
}
