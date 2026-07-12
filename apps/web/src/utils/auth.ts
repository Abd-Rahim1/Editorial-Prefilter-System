/*
Editor & Admin Authentication Helper Utility
Centralizes token storage retrieval, Axios authorization header injection, 
and safe 401 handling without triggering runtime error overlays.
*/
import axios, { AxiosRequestConfig } from 'axios';

export function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  const token = localStorage.getItem('token');
  if (token && token.trim() !== '') {
    return token.trim();
  }
  if (process.env.NEXT_PUBLIC_DEMO_AUTH_ENABLED === 'true') {
    return 'dummy-admin-token';
  }
  return '';
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export function handleUnauthorized(router?: any) {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
    document.cookie = 'user_role=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
    if (window.location.pathname !== '/login') {
      if (router && typeof router.replace === 'function') {
        router.replace('/login');
      } else {
        window.location.href = '/login';
      }
    }
  }
}

export async function authAxiosGet<T>(url: string, config: AxiosRequestConfig = {}): Promise<T | null> {
  const token = getAuthToken();
  if (!token) {
    handleUnauthorized();
    return null;
  }
  try {
    const res = await axios.get(url, {
      ...config,
      headers: {
        Authorization: `Bearer ${token}`,
        ...config.headers,
      },
    });
    return res.data;
  } catch (err: any) {
    if (err?.response?.status === 401) {
      handleUnauthorized();
      return null;
    }
    throw err;
  }
}

export async function authAxiosPost<T>(url: string, data?: any, config: AxiosRequestConfig = {}): Promise<T | null> {
  const token = getAuthToken();
  if (!token) {
    handleUnauthorized();
    return null;
  }
  try {
    const res = await axios.post(url, data, {
      ...config,
      headers: {
        Authorization: `Bearer ${token}`,
        ...config.headers,
      },
    });
    return res.data;
  } catch (err: any) {
    if (err?.response?.status === 401) {
      handleUnauthorized();
      return null;
    }
    throw err;
  }
}
