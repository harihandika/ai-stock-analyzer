import { apiClient } from './api';

export const authService = {
  async login(username: string, password: string) {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    
    const response = await apiClient.post('/auth/token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data; // { access_token, refresh_token, token_type }
  },

  async register(data: any) {
    const response = await apiClient.post('/auth/register', data);
    return response.data;
  },

  async getMe() {
    const response = await apiClient.get('/auth/me');
    return response.data; // User profile
  },

  async logout() {
    // Attempt to hit logout endpoint to revoke refresh token
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      console.error('Logout API failed', e);
    }
  }
};
