"use client";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";
import Cookies from "js-cookie";
import { authService } from "@/services/auth";
import { clearSession, storeSession } from "@/services/session";

export interface User {
  id: string;
  email: string;
  full_name: string;
  subscription_tier: string;
  created_at: string;
  quota_used: number;
  quota_reserved: number;
  quota_limit: number | null;
  quota_remaining: number | null;
  quota_reset_at: string;
}
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken?: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
}
const AuthContext = createContext<AuthContextType | undefined>(undefined);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const generation = useRef(0);
  const fetchUser = useCallback(async () => {
    const current = generation.current;
    try {
      const profile = await (Cookies.get("access_token") ||
      Cookies.get("refresh_token")
        ? authService.getMe()
        : Promise.resolve(null));
      if (current === generation.current) setUser(profile);
    } catch (error) {
      if (current === generation.current) {
        clearSession();
        setUser(null);
      }
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);
  useEffect(() => {
    const expired = () => {
      generation.current++;
      setUser(null);
    };
    window.addEventListener("auth-expired", expired);
    void fetchUser().catch(() => undefined);
    return () => window.removeEventListener("auth-expired", expired);
  }, [fetchUser]);
  const login = async (token: string, refreshToken?: string) => {
    generation.current++;
    setUser(null);
    storeSession(token, refreshToken);
    await fetchUser();
  };
  const logout = async () => {
    generation.current++;
    try {
      await authService.logout();
    } catch {
      window.alert(
        "Sesi lokal dihapus, tetapi server belum dapat mengonfirmasi pencabutan sesi.",
      );
    } finally {
      setUser(null);
      window.location.assign("/login");
    }
  };
  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
