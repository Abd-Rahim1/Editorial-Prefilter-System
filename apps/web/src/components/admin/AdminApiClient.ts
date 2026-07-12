/*
Admin API Client — Handles all HTTP requests from React to the FastAPI backend.
Follows clean architecture: React -> API Client -> FastAPI Router -> Service -> Repository -> PostgreSQL.
*/
const API_BASE = 'http://127.0.0.1:8000';

export async function adminFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || `HTTP Error ${res.status}`);
    }
    return await res.json();
  } catch (error) {
    console.warn(`[adminFetch] Error calling ${endpoint}:`, error);
    throw error;
  }
}

// ─── 1. EXECUTIVE OVERVIEW & EDITORIAL ANALYTICS ────────────────────────────
export async function getDashboardData() {
  return adminFetch<any>('/api/v1/admin/dashboard');
}

export async function getStatistics() {
  return adminFetch<any>('/api/v1/admin/statistics');
}

// ─── 2. POLICY THRESHOLDS ───────────────────────────────────────────────────
export async function getThresholds() {
  return adminFetch<{ auto_reject_threshold: number; manual_review_threshold: number }>('/api/v1/admin/thresholds');
}

export async function updateThresholds(reject: number, review: number) {
  return adminFetch<any>('/api/v1/admin/settings', {
    method: 'PATCH',
    body: JSON.stringify({ auto_reject_threshold: reject, manual_review_threshold: review }),
  });
}

// ─── 3. PROMPT MANAGEMENT ───────────────────────────────────────────────────
export async function getPrompts() {
  return adminFetch<any[]>('/api/v1/admin/prompts');
}

export async function createPrompt(data: any) {
  return adminFetch<any>('/api/v1/admin/prompts', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updatePrompt(id: number, data: any) {
  return adminFetch<any>(`/api/v1/admin/prompts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function activatePrompt(id: number) {
  return adminFetch<any>(`/api/v1/admin/prompts/${id}/activate`, { method: 'POST' });
}

export async function deletePrompt(id: number) {
  return adminFetch<any>(`/api/v1/admin/prompts/${id}`, { method: 'DELETE' });
}

// ─── 4. MODEL REGISTRY ──────────────────────────────────────────────────────
export async function getModels() {
  return adminFetch<any[]>('/api/v1/admin/models');
}

export async function updateModel(id: number, data: any) {
  return adminFetch<any>(`/api/v1/admin/models/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function activateModel(id: number) {
  return adminFetch<any>(`/api/v1/admin/models/${id}/activate`, { method: 'POST' });
}

export async function deleteModel(id: number) {
  return adminFetch<any>(`/api/v1/admin/models/${id}`, { method: 'DELETE' });
}

// ─── 5. EXPERIMENTS ─────────────────────────────────────────────────────────
export async function getExperiments() {
  return adminFetch<any[]>('/api/v1/admin/experiments');
}

// ─── 6. USERS & ROLES ───────────────────────────────────────────────────────
export async function getUsers() {
  return adminFetch<any[]>('/api/v1/admin/users');
}

export async function createUser(data: any) {
  return adminFetch<any>('/api/v1/admin/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateUser(id: number, data: any) {
  return adminFetch<any>(`/api/v1/admin/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteUser(id: number) {
  return adminFetch<any>(`/api/v1/admin/users/${id}`, { method: 'DELETE' });
}

export async function getRoles() {
  return adminFetch<any[]>('/api/v1/admin/roles');
}

// ─── 7. SYSTEM HEALTH & API METRICS ─────────────────────────────────────────
export async function getSystemHealth() {
  return adminFetch<any[]>('/api/v1/admin/system-health');
}

export async function getApiMetrics() {
  return adminFetch<any>('/api/v1/admin/api-metrics');
}

// ─── 8. AUDIT LOGS ──────────────────────────────────────────────────────────
export async function getAuditLogs(limit: number = 100) {
  return adminFetch<any[]>(`/api/v1/admin/audit?limit=${limit}`);
}
