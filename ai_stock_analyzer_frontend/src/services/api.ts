import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import Cookies from "js-cookie";
import { clearSession, storeSession } from "./session";

declare module "axios" {
  interface AxiosRequestConfig {
    skipAuthRefresh?: boolean;
  }
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: { "Content-Type": "application/json" },
});
const refreshClient = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });
let refreshing: Promise<string> | null = null;
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = "Bearer " + token;
  else delete config.headers.Authorization;
  return config;
});
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as
      (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const authRequest = /\/auth\/(token|register|refresh|logout)$/.test(
      config?.url || "",
    );
    if (
      !config ||
      config.skipAuthRefresh ||
      config.signal?.aborted ||
      error.response?.status !== 401 ||
      config._retry ||
      authRequest
    )
      throw error;
    config._retry = true;
    const currentAccess = Cookies.get("access_token");
    if (
      currentAccess &&
      config.headers.Authorization !== "Bearer " + currentAccess
    ) {
      config.headers.Authorization = "Bearer " + currentAccess;
      return apiClient(config);
    }
    const initialRefresh = Cookies.get("refresh_token");
    let refreshedAccess: string | undefined;
    if (!refreshing) {
      refreshing = (async () => {
        const token = Cookies.get("refresh_token");
        if (!token) throw new Error("Sesi berakhir. Silakan masuk kembali.");
        const { data } = await refreshClient.post("/auth/refresh", {
          refresh_token: token,
        });
        if (Cookies.get("refresh_token") !== token)
          throw new Error("Sesi telah berubah.");
        storeSession(data.access_token, data.refresh_token);
        return data.access_token as string;
      })().finally(() => {
        refreshing = null;
      });
    }
    try {
      refreshedAccess = await refreshing;
      config.headers.Authorization = "Bearer " + refreshedAccess;
      return await apiClient(config);
    } catch (refreshError) {
      const stillOwnsSession = refreshedAccess
        ? Cookies.get("access_token") === refreshedAccess
        : Cookies.get("refresh_token") === initialRefresh;
      if (!stillOwnsSession) throw refreshError;
      clearSession();
      // AuthProvider receives auth-expired and the protected layout owns navigation.
      // Multiple concurrent 401s must not launch competing full-page redirects.
      throw refreshError;
    }
  },
);
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (detail?.message) return detail.message;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
    return error.code === "ECONNABORTED"
      ? "Permintaan melewati batas waktu."
      : "Layanan tidak dapat dihubungi. Silakan coba lagi.";
  }
  return error instanceof Error
    ? error.message
    : "Terjadi kesalahan. Silakan coba lagi.";
}
export const logout = (refreshToken: string) =>
  apiClient.post("/auth/logout", { refresh_token: refreshToken });
export const updatePassword = (currentPw: string, newPw: string) =>
  apiClient.post("/auth/change-password", {
    current_password: currentPw,
    new_password: newPw,
  });
export const getUserQuota = () => apiClient.get("/auth/me");
export const runBacktest = (
  ticker: string,
  params: {
    years: number;
    target_profit_pct: number;
    stop_loss_pct: number;
    initial_capital?: number;
    lot_size?: number;
    buy_fee_bps?: number;
    sell_fee_bps?: number;
    slippage_bps?: number;
  },
) =>
  apiClient.post(
    "/analysis/" + encodeURIComponent(ticker) + "/backtest",
    params,
  );
