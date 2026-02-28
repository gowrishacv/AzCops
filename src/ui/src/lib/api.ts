import { InteractionRequiredAuthError } from '@azure/msal-browser';
import { msalInstance, apiTokenRequest, AUTH_ENABLED } from '@/lib/msal';
import { matchMockRoute } from '@/lib/mock-data';

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true';

/* ------------------------------------------------------------------ */
/* Token acquisition                                                   */
/* ------------------------------------------------------------------ */

async function getAccessToken(): Promise<string | null> {
  // Dev bypass — no token needed when auth is disabled
  if (!AUTH_ENABLED) return null;

  const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0];
  if (!account) return null;

  // No API scope configured → skip token acquisition
  if (apiTokenRequest.scopes.length === 0) return null;

  try {
    const response = await msalInstance.acquireTokenSilent({
      ...apiTokenRequest,
      account,
    });
    return response.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      // Token expired or consent required — redirect to login
      await msalInstance.acquireTokenRedirect(apiTokenRequest);
      return null;
    }
    console.error('Token acquisition failed:', error);
    return null;
  }
}

/* ------------------------------------------------------------------ */
/* Authenticated fetch                                                 */
/* ------------------------------------------------------------------ */

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  // Mock mode — return fake data immediately (no network)
  if (USE_MOCK) {
    const mock = matchMockRoute(path);
    if (mock !== null) {
      // Simulate network delay for realistic UX
      await new Promise((r) => setTimeout(r, 300 + Math.random() * 400));
      return mock as T;
    }
  }

  try {
    const token = await getAccessToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${BASE}${path}`, { ...options, headers });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? `HTTP ${res.status}`);
    }

    return res.json() as Promise<T>;
  } catch (error) {
    // Fallback to mock data when API is unreachable
    const mock = matchMockRoute(path);
    if (mock !== null) {
      console.warn(`[AzCops] API unreachable, using mock data for ${path}`);
      return mock as T;
    }
    throw error;
  }
}

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

export interface Tenant {
  id: string;
  name: string;
  azure_tenant_id: string;
  type: string;
  is_active: boolean;
}

export interface Subscription {
  id: string;
  subscription_id: string;
  display_name: string;
  is_active: boolean;
}

export interface CostSummary {
  total_cost: number;
  currency: string;
  period_days: number;
  by_service: { service_name: string; total_cost: number }[];
  daily_trend: { date: string; total_cost: number }[];
}

export interface Recommendation {
  id: string;
  tenant_id: string;
  rule_id: string;
  category: string;
  estimated_monthly_savings: number;
  confidence_score: number;
  risk_level: string;
  effort_level: string;
  status: string;
  short_description: string;
  detail: string;
  resource_id: string;
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  resource_group: string;
  location: string;
  tags: Record<string, string>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  version: string;
}

export interface IngestionRun {
  run_id: string;
  status: string;
  tenant_id: string;
  started_at: string | null;
  completed_at: string | null;
  subscriptions_processed: number;
  subscriptions_failed: number;
}

/* ------------------------------------------------------------------ */
/* API namespaces                                                      */
/* ------------------------------------------------------------------ */

// Health
export const healthApi = {
  check: () => apiFetch<HealthResponse>('/health'),
};

// Tenants
export const tenantsApi = {
  list: (page = 1, size = 50) =>
    apiFetch<PaginatedResponse<Tenant>>(`/tenants?page=${page}&size=${size}`),
  get: (id: string) => apiFetch<Tenant>(`/tenants/${id}`),
};

// Subscriptions
export const subscriptionsApi = {
  list: (page = 1, size = 50) =>
    apiFetch<PaginatedResponse<Subscription>>(`/subscriptions?page=${page}&size=${size}`),
};

// Costs
export const costsApi = {
  summary: (days = 30) => apiFetch<CostSummary>(`/costs/summary?days=${days}`),
};

// Recommendations
export const recommendationsApi = {
  list: (params?: {
    status?: string;
    category?: string;
    risk_level?: string;
    page?: number;
    size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.category) q.set('category', params.category);
    if (params?.risk_level) q.set('risk_level', params.risk_level);
    q.set('page', String(params?.page ?? 1));
    q.set('size', String(params?.size ?? 50));
    return apiFetch<PaginatedResponse<Recommendation>>(`/recommendations?${q}`);
  },
  approve: (id: string) =>
    apiFetch<Recommendation>(`/recommendations/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason?: string) =>
    apiFetch<Recommendation>(`/recommendations/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  dismiss: (id: string) =>
    apiFetch<Recommendation>(`/recommendations/${id}/dismiss`, { method: 'POST' }),
  generate: (tenantId?: string) =>
    apiFetch<{ count: number; message: string }>('/recommendations/generate', {
      method: 'POST',
      body: JSON.stringify(tenantId ? { tenant_id: tenantId } : {}),
    }),
};

// Resources
export const resourcesApi = {
  list: (page = 1, size = 50) =>
    apiFetch<PaginatedResponse<Resource>>(`/resources?page=${page}&size=${size}`),
};

// Ingestion
export const ingestionApi = {
  trigger: (data: {
    tenant_db_id: string;
    azure_tenant_id: string;
    subscription_ids?: string[];
  }) =>
    apiFetch<{ run_id: string; status: string; message: string }>('/ingestion/trigger', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  status: (runId: string) => apiFetch<IngestionRun>(`/ingestion/status/${runId}`),
};
