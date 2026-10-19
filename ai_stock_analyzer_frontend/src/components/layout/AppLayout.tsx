"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  LayoutDashboard,
  LineChart,
  Star,
  Settings,
  LogOut,
  Search,
  Bell,
  User as UserIcon,
  Menu,
} from "lucide-react";
import Link from "next/link";
import clsx from "clsx";
import { apiClient, errorMessage } from "@/services/api";
import { Stock } from "@/services/market";
import styles from "./layout.module.css";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated, isLoading, logout, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // States
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Stock[]>([]);
  const [searchError, setSearchError] = useState("");
  const [activeResult, setActiveResult] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const searchRef = useRef<HTMLFormElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);
  const notificationsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        searchRef.current &&
        !searchRef.current.contains(event.target as Node)
      ) {
        setIsSearchOpen(false);
      }
      if (
        settingsRef.current &&
        !settingsRef.current.contains(event.target as Node)
      ) {
        setIsSettingsOpen(false);
      }
      if (
        notificationsRef.current &&
        !notificationsRef.current.contains(event.target as Node)
      ) {
        setIsNotificationsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      if (searchQuery.trim().length < 2) {
        setIsSearchOpen(false);
        setIsSearching(false);
        return;
      }
      setIsSearching(true);
      setIsSearchOpen(true);
      try {
        const res = await apiClient.get("/stocks", {
          params: { q: searchQuery, per_page: 5 },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setSearchResults(res.data.data);
      } catch (error) {
        if (!controller.signal.aborted) setSearchError(errorMessage(error));
      } finally {
        if (!controller.signal.aborted) setIsSearching(false);
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [searchQuery]);

  if (isLoading || !isAuthenticated) {
    return (
      <div
        style={{
          display: "flex",
          minHeight: "100vh",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        Loading...
      </div>
    );
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const stock = searchResults[activeResult];
    if (stock) {
      setIsSearchOpen(false);
      setSearchQuery("");
      router.push("/stock/" + encodeURIComponent(stock.ticker));
    } else {
      setIsSearchOpen(true);
      setSearchError("Pilih hasil pencarian yang sesuai.");
    }
  };

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Watchlist", href: "/watchlist", icon: Star },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <div className={styles.layoutContainer}>
      {/* Mobile Sidebar Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-10 md:hidden backdrop-blur-sm"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(styles.sidebar, isMobileMenuOpen && styles.mobileOpen)}
      >
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
                <span
                  className={clsx(
                    styles.navItem,
                    isActive && styles.navItemActive,
                  )}
                >
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
              {user?.full_name?.charAt(0) || "U"}
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
          <div className="flex items-center">
            <button
              className={styles.mobileMenuBtn}
              aria-label="Buka navigasi"
              onClick={() => setIsMobileMenuOpen(true)}
            >
              <Menu width={24} height={24} />
            </button>
            <form
              ref={searchRef}
              onSubmit={handleSearch}
              className={styles.searchForm}
            >
              <Search className={styles.searchIcon} />
              <input
                type="text"
                placeholder="Cari Ticker atau Nama Perusahaan..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSearchError("");
                  setActiveResult(0);
                  setSearchResults([]);
                }}
                onFocus={() => {
                  if (searchResults.length > 0) setIsSearchOpen(true);
                }}
                aria-label="Cari saham"
                aria-expanded={isSearchOpen}
                aria-controls="stock-search-results"
                aria-activedescendant={
                  isSearchOpen && searchResults.length
                    ? "stock-option-" + activeResult
                    : undefined
                }
                role="combobox"
                onKeyDown={(e) => {
                  if (e.key === "ArrowDown" && searchResults.length) {
                    e.preventDefault();
                    setActiveResult((i) =>
                      Math.min(i + 1, searchResults.length - 1),
                    );
                  }
                  if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setActiveResult((i) => Math.max(0, i - 1));
                  }
                  if (e.key === "Escape") setIsSearchOpen(false);
                }}
                className={styles.searchInput}
              />
              {isSearchOpen && (
                <div
                  id="stock-search-results"
                  role="listbox"
                  aria-label="Hasil pencarian saham"
                  className={clsx(styles.dropdown, styles.searchDropdown)}
                >
                  {isSearching ? (
                    <div
                      className={styles.dropdownItem}
                      style={{ justifyContent: "center" }}
                    >
                      Mencari...
                    </div>
                  ) : searchResults.length > 0 ? (
                    searchResults.map((stock, index) => (
                      <button
                        key={stock.ticker}
                        id={"stock-option-" + index}
                        role="option"
                        aria-selected={index === activeResult}
                        type="button"
                        className={styles.dropdownItem}
                        onClick={() => {
                          setIsSearchOpen(false);
                          setSearchQuery("");
                          router.push(`/stock/${stock.ticker}`);
                        }}
                      >
                        <span style={{ fontWeight: "bold" }}>
                          {stock.ticker}
                        </span>
                        <span
                          style={{
                            color: "var(--text-muted)",
                            fontSize: "0.75rem",
                          }}
                        >
                          {stock.company_name} ·{" "}
                          {stock.exchange || "Bursa belum diketahui"} ·{" "}
                          {stock.currency || "?"}
                        </span>
                      </button>
                    ))
                  ) : (
                    <div
                      className={styles.dropdownItem}
                      style={{ justifyContent: "center" }}
                    >
                      {searchError || "Saham tidak ditemukan"}
                    </div>
                  )}
                  {!searchResults.length &&
                    /^[A-Za-z0-9^][A-Za-z0-9.^=-]{0,19}$/.test(searchQuery) && (
                      <button
                        type="button"
                        className={styles.dropdownItem}
                        onClick={() => {
                          setIsSearchOpen(false);
                          router.push(
                            "/stock/" +
                              encodeURIComponent(searchQuery.toUpperCase()),
                          );
                        }}
                      >
                        Buka ticker untuk sinkronisasi:{" "}
                        {searchQuery.toUpperCase()}
                      </button>
                    )}
                </div>
              )}
            </form>
          </div>

          <div className={styles.headerActions}>
            <div ref={notificationsRef} style={{ position: "relative" }}>
              <button
                className={styles.actionBtn}
                aria-label="Notifikasi"
                onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              >
                <Bell width={20} height={20} />
              </button>
              {isNotificationsOpen && (
                <div className={styles.dropdown} style={{ minWidth: "250px" }}>
                  <div className={styles.dropdownHeader}>Notifications</div>
                  <div
                    className={styles.dropdownItem}
                    style={{
                      flexDirection: "column",
                      alignItems: "flex-start",
                      padding: "12px 16px",
                      gap: "4px",
                    }}
                  >
                    <span style={{ fontSize: "0.875rem", color: "white" }}>
                      Belum ada notifikasi
                    </span>
                    <span
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      Riwayat notifikasi belum tersedia. Status pembaruan
                      ditampilkan pada halaman saham.
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div ref={settingsRef} style={{ position: "relative" }}>
              <button
                className={styles.actionBtn}
                aria-label="Menu akun"
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              >
                <Settings width={20} height={20} />
              </button>
              {isSettingsOpen && (
                <div className={styles.dropdown}>
                  <div className={styles.dropdownHeader}>Akun Saya</div>
                  <Link
                    href="/settings"
                    className={styles.dropdownItem}
                    onClick={() => setIsSettingsOpen(false)}
                  >
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <UserIcon size={16} /> Profil
                    </span>
                  </Link>
                  <div
                    style={{
                      height: "1px",
                      background: "var(--glass-border)",
                      margin: "4px 0",
                    }}
                  ></div>
                  <button
                    onClick={logout}
                    className={styles.dropdownItem}
                    style={{ color: "#fb7185" }}
                  >
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <LogOut size={16} /> Sign Out
                    </span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Scrollable Page Content */}
        <div className={styles.pageContent}>{children}</div>
      </main>
    </div>
  );
}
