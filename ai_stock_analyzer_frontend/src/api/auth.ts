import axios from 'axios';
import Cookies from 'js-cookie';

const API_URL = 'http://localhost:8000';

const authApi = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor untuk menyematkan token pada setiap request
authApi.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = async (email: string, password: string) => {
  try {
    const response = await authApi.post('/auth/token', {
      email,
      password,
    });
    
    const { access_token, refresh_token } = response.data;
    
    // Simpan token ke Cookies
    Cookies.set('access_token', access_token, { expires: 1 }); // 1 hari
    Cookies.set('refresh_token', refresh_token, { expires: 7 }); // 7 hari
    
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Terjadi kesalahan saat login');
  }
};

export const register = async (full_name: string, email: string, password: string) => {
  try {
    const response = await authApi.post('/auth/register', {
      full_name,
      email,
      password,
    });
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Terjadi kesalahan saat registrasi');
  }
};

export const logout = () => {
  Cookies.remove('access_token');
  Cookies.remove('refresh_token');
  window.location.href = '/login';
};

export const getCurrentUser = async () => {
  try {
    const response = await authApi.get('/auth/me');
    return response.data;
  } catch (error) {
    logout();
    throw error;
  }
};

export default authApi;
