import Cookies from "js-cookie";
import { apiClient, logout } from "./api";
import { clearSession } from "./session";
export const authService = {
  async login(email: string, password: string) {
    return (await apiClient.post("/auth/token", { email, password })).data;
  },
  async register(data: { full_name: string; email: string; password: string }) {
    return (await apiClient.post("/auth/register", data)).data;
  },
  async getMe() {
    return (await apiClient.get("/auth/me")).data;
  },
  async logout() {
    try {
      const token = Cookies.get("refresh_token");
      if (token) await logout(token);
    } finally {
      clearSession();
    }
  },
};
