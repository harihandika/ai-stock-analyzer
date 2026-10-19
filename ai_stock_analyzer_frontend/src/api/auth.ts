import { authService } from "@/services/auth";
import { apiClient, errorMessage } from "@/services/api";
export const login = async (email: string, password: string) => {
  try {
    return await authService.login(email, password);
  } catch (error) {
    throw new Error(errorMessage(error));
  }
};
export const register = async (
  full_name: string,
  email: string,
  password: string,
) => {
  try {
    return await authService.register({ full_name, email, password });
  } catch (error) {
    throw new Error(errorMessage(error));
  }
};
export const logout = authService.logout;
export const getCurrentUser = authService.getMe;
export default apiClient;
