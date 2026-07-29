'use client';

import { useState, useEffect } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import { getUserQuota, logout } from '@/services/api';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

interface UserData {
  id: string;
  email: string;
  full_name: string;
  subscription_tier: string;
  analysis_quota_used: number;
  created_at: string;
}

export default function SettingsPage() {
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await getUserQuota();
        setUser(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to fetch user data');
        if (err.response?.status === 401) {
          router.push('/login');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchUserData();
  }, [router]);

  const handleLogout = async () => {
    try {
      const refreshToken = Cookies.get('refresh_token');
      if (refreshToken) {
        await logout(refreshToken);
      }
    } catch (e) {
      console.error('Logout error', e);
    } finally {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      router.push('/login');
    }
  };

  const maxQuota = user?.subscription_tier === 'premium' ? 'Unlimited' : 3;

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto py-8">
        <h1 className="text-3xl font-bold mb-8">Account Settings</h1>
        
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-lg mb-6">
            {error}
          </div>
        ) : user ? (
          <div className="space-y-6">
            {/* Profile Card */}
            <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Profile Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <p className="text-sm text-gray-400">Full Name</p>
                  <p className="text-lg font-medium">{user.full_name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Email Address</p>
                  <p className="text-lg font-medium">{user.email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Subscription Tier</p>
                  <span className={`inline-block mt-1 px-3 py-1 rounded-full text-xs font-semibold ${
                    user.subscription_tier === 'premium' ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/50' : 'bg-gray-700 text-gray-300'
                  }`}>
                    {user.subscription_tier.toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Member Since</p>
                  <p className="text-lg font-medium">
                    {new Date(user.created_at).toLocaleDateString('id-ID', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </p>
                </div>
              </div>
            </div>

            {/* Quota Card */}
            <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">AI Analysis Quota</h2>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 mb-2">Usage Today</p>
                  <p className="text-3xl font-bold">
                    <span className={user.analysis_quota_used >= (maxQuota as number) && maxQuota !== 'Unlimited' ? 'text-red-500' : 'text-primary-500'}>
                      {user.analysis_quota_used}
                    </span>
                    <span className="text-gray-500 text-xl font-normal"> / {maxQuota}</span>
                  </p>
                </div>
                {maxQuota !== 'Unlimited' && (
                  <div className="w-1/2">
                    <div className="h-4 w-full bg-dark-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${user.analysis_quota_used >= 3 ? 'bg-red-500' : 'bg-primary-500'}`} 
                        style={{ width: `${Math.min((user.analysis_quota_used / 3) * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end pt-4">
              <button 
                onClick={handleLogout}
                className="bg-red-500/20 hover:bg-red-500/30 text-red-500 border border-red-500/50 px-6 py-2 rounded-lg font-medium transition-colors"
              >
                Log Out
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </AppLayout>
  );
}
