const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Types
export interface Tenant { id: string; name: string; azure_tenant_id: string; type: string; is_active: boolean; }
export interface Subscription { id: string; subscription_id: string; display_name: string; is_active: boolean; }
export interface CostSummary { total_cost: number; currency: string; period_days: number; by_service: { service_name: string; total_cost: number }[]; daily_trend: { date: string; total_cost: number }[]; }
export interface Recommendation { id: string; tenant_id: string; rule_id: string; category: string; estimated_monthly_savings: number; confidence_score: number; risk_level: string; effort_level: string; status: string; short_description: string; detail: string; resource_id: string; }
export interface PaginatedResponse<T> { items: T[]; total: number; page: number; size: number; pages: number; }
export interface HealthResponse { status: string; database: string; version: string; }

// Health
export const healthApi = {
  check: () => apiFetch<HealthResponse>('/health'),
};

// Tenants
export const tenantsApi = {
  list: (page = 1, size = 50) => apiFetch<PaginatedResponse<Tenant>>(`/tenants?page=${page}&size=${size}`),
  get: (id: string) => apiFetch<Tenant>(`/tenants/${id}`),
};

// Subscriptions
export const subscriptionsApi = {
  list: (page = 1, size = 50) => apiFetch<PaginatedResponse<Subscription>>(`/subscriptions?page=${page}&size=${size}`),
};

// Costs
export const costsApi = {
  summary: (days = 30) => apiFetch<CostSummary>(`/costs/summary?days=${days}`),
};

// Recommendations
export const recommendationsApi = {
  list: (params?: { status?: string; category?: string; risk_level?: string; page?: number; size?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.category) q.set('category', params.category);
    if (params?.risk_level) q.set('risk_level', params.risk_level);
    q.set('page', String(params?.page ?? 1));
    q.set('size', String(params?.size ?? 50));
    return apiFetch<PaginatedResponse<Recommendation>>(`/recommendations?${q}`);
  },
  approve: (id: string) => apiFetch<Recommendation>(`/recommendations/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason?: string) => apiFetch<Recommendation>(`/recommendations/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  dismiss: (id: string) => apiFetch<Recommendation>(`/recommendations/${id}/dismiss`, { method: 'POST' }),
  generate: (subscriptionId: string) => apiFetch<{ count: number }>('/recommendations/generate', { method: 'POST', body: JSON.stringify({ subscription_id: subscriptionId }) }),
};
