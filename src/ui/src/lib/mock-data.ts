/**
 * Realistic mock data for AzCops dashboard.
 * Used when the API is unavailable (local dev without backend running).
 */

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/* ------------------------------------------------------------------ */
/* Cost data                                                           */
/* ------------------------------------------------------------------ */
function generateDailyTrend(days: number) {
  const trend = [];
  const baseSpend = 420;
  for (let i = days - 1; i >= 0; i--) {
    const weekday = new Date(Date.now() - i * 86400000).getDay();
    const weekendDip = weekday === 0 || weekday === 6 ? 0.72 : 1;
    const noise = 0.88 + Math.random() * 0.24;
    const spike = i === Math.floor(days * 0.3) ? 1.6 : 1;
    trend.push({
      date: daysAgo(i),
      total_cost: Math.round(baseSpend * weekendDip * noise * spike * 100) / 100,
    });
  }
  return trend;
}

const serviceBreakdown = [
  { service_name: 'Virtual Machines', total_cost: 4280.5 },
  { service_name: 'Azure SQL Database', total_cost: 2150.3 },
  { service_name: 'Storage Accounts', total_cost: 1420.8 },
  { service_name: 'App Service', total_cost: 980.2 },
  { service_name: 'Azure Kubernetes Service', total_cost: 870.6 },
  { service_name: 'Cosmos DB', total_cost: 650.4 },
  { service_name: 'Azure Functions', total_cost: 320.1 },
  { service_name: 'Load Balancer', total_cost: 280.9 },
  { service_name: 'Azure Monitor', total_cost: 190.5 },
  { service_name: 'Key Vault', total_cost: 45.2 },
];

export function mockCostSummary(days: number) {
  const trend = generateDailyTrend(days);
  const total = trend.reduce((s, d) => s + d.total_cost, 0);
  const scale = days / 30;
  return {
    total_cost: Math.round(total * 100) / 100,
    currency: 'USD',
    period_days: days,
    by_service: serviceBreakdown.map((s) => ({
      ...s,
      total_cost: Math.round(s.total_cost * scale * 100) / 100,
    })),
    daily_trend: trend,
  };
}

/* ------------------------------------------------------------------ */
/* Recommendations                                                     */
/* ------------------------------------------------------------------ */
const allRecommendations = [
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'WASTE-001',
    category: 'waste_detection', estimated_monthly_savings: 340.0, confidence_score: 0.95,
    risk_level: 'low', effort_level: 'low', status: 'open',
    short_description: 'Delete 4 unattached managed disks in rg-production-weu',
    detail: 'Four Premium SSD disks (P30) have been unattached for over 30 days. Deleting them saves $340/mo.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-production-weu/providers/Microsoft.Compute/disks/disk-orphaned-01',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'SIZE-001',
    category: 'right_sizing', estimated_monthly_savings: 520.0, confidence_score: 0.88,
    risk_level: 'medium', effort_level: 'medium', status: 'open',
    short_description: 'Downsize VM vm-api-prod-01 from D8s_v5 to D4s_v5',
    detail: 'Average CPU utilization is 8.2% over the last 14 days. Right-sizing from D8s to D4s saves 50%.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-production-weu/providers/Microsoft.Compute/virtualMachines/vm-api-prod-01',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'RATE-001',
    category: 'rate_optimization', estimated_monthly_savings: 1240.0, confidence_score: 0.92,
    risk_level: 'low', effort_level: 'high', status: 'open',
    short_description: 'Purchase 1-year RI for 3 D4s_v5 VMs (37% discount)',
    detail: 'Three D4s_v5 VMs have been running 24/7 for 90+ days. A 1-year reservation saves $1,240/mo.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-production-weu/providers/Microsoft.Compute/virtualMachines/vm-web-prod-01',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'WASTE-002',
    category: 'waste_detection', estimated_monthly_savings: 86.4, confidence_score: 0.98,
    risk_level: 'low', effort_level: 'low', status: 'open',
    short_description: 'Release 6 orphaned public IP addresses',
    detail: 'Six static public IPs are not associated with any resource. Releasing them saves $14.40 each.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-staging-weu/providers/Microsoft.Network/publicIPAddresses/pip-orphaned-01',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'GOV-001',
    category: 'governance', estimated_monthly_savings: 0, confidence_score: 1.0,
    risk_level: 'low', effort_level: 'low', status: 'open',
    short_description: '23 resources missing CostCenter tag in rg-dev-weu',
    detail: 'Resources without CostCenter tags cannot be attributed to business units for chargeback.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-dev-weu',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'SIZE-002',
    category: 'right_sizing', estimated_monthly_savings: 280.0, confidence_score: 0.82,
    risk_level: 'medium', effort_level: 'medium', status: 'open',
    short_description: 'Downsize App Service Plan asp-backend from P2v3 to P1v3',
    detail: 'The plan averages 12% CPU utilization. Downsizing from P2v3 to P1v3 halves the compute cost.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-production-weu/providers/Microsoft.Web/serverFarms/asp-backend',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'WASTE-004',
    category: 'waste_detection', estimated_monthly_savings: 156.0, confidence_score: 0.97,
    risk_level: 'low', effort_level: 'low', status: 'open',
    short_description: 'Delete 12 snapshots older than 90 days (3.1 TB)',
    detail: 'Stale snapshots from old backup jobs. Deleting 3.1 TB of snapshots saves $156/mo in storage.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-backups-weu/providers/Microsoft.Compute/snapshots/snap-old-01',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'SIZE-003',
    category: 'right_sizing', estimated_monthly_savings: 410.0, confidence_score: 0.85,
    risk_level: 'high', effort_level: 'high', status: 'open',
    short_description: 'Downsize SQL Database sqldb-analytics from S3 to S1',
    detail: 'DTU utilization averages 15% over 30 days. Downsizing from S3 (100 DTU) to S1 (20 DTU) saves $410/mo.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-data-weu/providers/Microsoft.Sql/servers/sql-analytics/databases/sqldb-analytics',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'RATE-002',
    category: 'rate_optimization', estimated_monthly_savings: 680.0, confidence_score: 0.78,
    risk_level: 'low', effort_level: 'medium', status: 'approved',
    short_description: 'Purchase Azure Savings Plan for consistent compute spend',
    detail: 'Monthly compute spend averages $3,400 with low variance. A 1-year Savings Plan provides ~20% discount.',
    resource_id: '/subscriptions/sub-1',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'GOV-002',
    category: 'governance', estimated_monthly_savings: 0, confidence_score: 0.9,
    risk_level: 'high', effort_level: 'low', status: 'open',
    short_description: 'Subscription approaching 85% of monthly budget ($12,000)',
    detail: 'Current month spend is $10,200 with 8 days remaining. Projected end-of-month spend: $13,600 (13% over budget).',
    resource_id: '/subscriptions/sub-1',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'WASTE-003',
    category: 'waste_detection', estimated_monthly_savings: 42.0, confidence_score: 0.96,
    risk_level: 'low', effort_level: 'low', status: 'executed',
    short_description: 'Deleted 8 orphaned NICs from decommissioned VMs',
    detail: 'Eight network interfaces had no associated VM. Already cleaned up.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-legacy-weu/providers/Microsoft.Network/networkInterfaces/nic-orphaned-01',
  },
  {
    id: uuid(), tenant_id: 'tenant-1', rule_id: 'SIZE-001',
    category: 'right_sizing', estimated_monthly_savings: 260.0, confidence_score: 0.91,
    risk_level: 'medium', effort_level: 'medium', status: 'rejected',
    short_description: 'Downsize VM vm-batch-01 from E8s_v5 to E4s_v5',
    detail: 'Rejected: batch jobs spike to 90% CPU on weekends. Average is misleading for batch workloads.',
    resource_id: '/subscriptions/sub-1/resourceGroups/rg-batch-weu/providers/Microsoft.Compute/virtualMachines/vm-batch-01',
  },
];

export function mockRecommendations(params?: {
  status?: string;
  category?: string;
  risk_level?: string;
  page?: number;
  size?: number;
}) {
  let filtered = [...allRecommendations];
  if (params?.status) filtered = filtered.filter((r) => r.status === params.status);
  if (params?.category) filtered = filtered.filter((r) => r.category === params.category);
  if (params?.risk_level) filtered = filtered.filter((r) => r.risk_level === params.risk_level);

  const page = params?.page ?? 1;
  const size = params?.size ?? 20;
  const start = (page - 1) * size;
  const items = filtered.slice(start, start + size);

  return {
    items,
    total: filtered.length,
    page,
    size,
    pages: Math.ceil(filtered.length / size),
  };
}

/* ------------------------------------------------------------------ */
/* Resources                                                           */
/* ------------------------------------------------------------------ */
const allResources = [
  { id: uuid(), name: 'vm-api-prod-01', type: 'Microsoft.Compute/virtualMachines', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001', Team: 'Platform' } },
  { id: uuid(), name: 'vm-api-prod-02', type: 'Microsoft.Compute/virtualMachines', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001', Team: 'Platform' } },
  { id: uuid(), name: 'vm-web-prod-01', type: 'Microsoft.Compute/virtualMachines', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1002', Team: 'Frontend' } },
  { id: uuid(), name: 'vm-batch-01', type: 'Microsoft.Compute/virtualMachines', resource_group: 'rg-batch-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1003' } },
  { id: uuid(), name: 'sqldb-analytics', type: 'Microsoft.Sql/servers/databases', resource_group: 'rg-data-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1004', Team: 'Data' } },
  { id: uuid(), name: 'sql-primary', type: 'Microsoft.Sql/servers', resource_group: 'rg-data-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1004' } },
  { id: uuid(), name: 'cosmos-orders', type: 'Microsoft.DocumentDB/databaseAccounts', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001', Team: 'Backend' } },
  { id: uuid(), name: 'stproddata001', type: 'Microsoft.Storage/storageAccounts', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001' } },
  { id: uuid(), name: 'stbackup001', type: 'Microsoft.Storage/storageAccounts', resource_group: 'rg-backups-weu', location: 'westeurope', tags: { Environment: 'Production' } },
  { id: uuid(), name: 'kv-prod-weu', type: 'Microsoft.KeyVault/vaults', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001' } },
  { id: uuid(), name: 'asp-backend', type: 'Microsoft.Web/serverFarms', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1002' } },
  { id: uuid(), name: 'app-frontend', type: 'Microsoft.Web/sites', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1002', Team: 'Frontend' } },
  { id: uuid(), name: 'aks-platform', type: 'Microsoft.ContainerService/managedClusters', resource_group: 'rg-aks-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1005', Team: 'Platform', 'kubernetes.io/cluster': 'aks-platform' } },
  { id: uuid(), name: 'func-notifications', type: 'Microsoft.Web/sites', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001' } },
  { id: uuid(), name: 'lb-frontend', type: 'Microsoft.Network/loadBalancers', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production' } },
  { id: uuid(), name: 'vnet-prod-weu', type: 'Microsoft.Network/virtualNetworks', resource_group: 'rg-networking-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1006' } },
  { id: uuid(), name: 'nsg-api', type: 'Microsoft.Network/networkSecurityGroups', resource_group: 'rg-networking-weu', location: 'westeurope', tags: {} },
  { id: uuid(), name: 'pip-orphaned-01', type: 'Microsoft.Network/publicIPAddresses', resource_group: 'rg-staging-weu', location: 'westeurope', tags: {} },
  { id: uuid(), name: 'disk-orphaned-01', type: 'Microsoft.Compute/disks', resource_group: 'rg-production-weu', location: 'westeurope', tags: {} },
  { id: uuid(), name: 'monitor-workspace', type: 'Microsoft.OperationalInsights/workspaces', resource_group: 'rg-monitoring-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1006' } },
  { id: uuid(), name: 'appi-prod', type: 'Microsoft.Insights/components', resource_group: 'rg-monitoring-weu', location: 'westeurope', tags: { Environment: 'Production' } },
  { id: uuid(), name: 'redis-cache-prod', type: 'Microsoft.Cache/Redis', resource_group: 'rg-production-weu', location: 'westeurope', tags: { Environment: 'Production', CostCenter: 'CC-1001', Team: 'Backend' } },
  { id: uuid(), name: 'vm-dev-01', type: 'Microsoft.Compute/virtualMachines', resource_group: 'rg-dev-weu', location: 'westeurope', tags: { Environment: 'Development' } },
  { id: uuid(), name: 'vm-staging-01', type: 'Microsoft.Compute/virtualMachines', resource_group: 'rg-staging-weu', location: 'westeurope', tags: { Environment: 'Staging' } },
];

export function mockResources(size = 50) {
  return {
    items: allResources.slice(0, size),
    total: allResources.length,
    page: 1,
    size,
    pages: 1,
  };
}

/* ------------------------------------------------------------------ */
/* Tenants                                                             */
/* ------------------------------------------------------------------ */
const allTenants = [
  { id: 'tenant-1', name: 'Contoso Production', azure_tenant_id: 'a9b6ecd7-61b4-4f3d-b189-90b20256eb11', type: 'internal', is_active: true },
  { id: 'tenant-2', name: 'Fabrikam Staging', azure_tenant_id: 'c4d7f8e9-2a1b-4c3d-8e5f-a6b7c8d9e0f1', type: 'external', is_active: true },
  { id: 'tenant-3', name: 'Northwind Dev', azure_tenant_id: 'e1f2a3b4-5c6d-7e8f-9a0b-c1d2e3f4a5b6', type: 'internal', is_active: false },
];

export function mockTenants(page = 1, size = 50) {
  return { items: allTenants.slice(0, size), total: allTenants.length, page, size, pages: 1 };
}

/* ------------------------------------------------------------------ */
/* Subscriptions                                                       */
/* ------------------------------------------------------------------ */
const allSubscriptions = [
  { id: 'sub-1', subscription_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', display_name: 'Production Workloads', is_active: true },
  { id: 'sub-2', subscription_id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901', display_name: 'Staging Environment', is_active: true },
  { id: 'sub-3', subscription_id: 'c3d4e5f6-a7b8-9012-cdef-123456789012', display_name: 'Development & Test', is_active: true },
  { id: 'sub-4', subscription_id: 'd4e5f6a7-b8c9-0123-defa-234567890123', display_name: 'Shared Services', is_active: true },
  { id: 'sub-5', subscription_id: 'e5f6a7b8-c9d0-1234-efab-345678901234', display_name: 'Legacy Migration', is_active: false },
];

export function mockSubscriptions(page = 1, size = 50) {
  return { items: allSubscriptions.slice(0, size), total: allSubscriptions.length, page, size, pages: 1 };
}

/* ------------------------------------------------------------------ */
/* Health                                                              */
/* ------------------------------------------------------------------ */
export function mockHealth() {
  return {
    status: 'healthy',
    database: 'postgresql',
    version: '0.1.0',
  };
}

/* ------------------------------------------------------------------ */
/* Mock API route matching                                             */
/* ------------------------------------------------------------------ */
export function matchMockRoute(path: string): unknown | null {
  // Health
  if (path === '/health') return mockHealth();

  // Tenants
  if (path.startsWith('/tenants')) {
    const singleMatch = path.match(/^\/tenants\/([^?/]+)$/);
    if (singleMatch) return allTenants.find((t) => t.id === singleMatch[1]) ?? allTenants[0];
    return mockTenants();
  }

  // Subscriptions
  if (path.startsWith('/subscriptions')) return mockSubscriptions();

  // Costs
  if (path.startsWith('/costs/summary')) {
    const costMatch = path.match(/days=(\d+)/);
    return mockCostSummary(costMatch ? parseInt(costMatch[1], 10) : 30);
  }

  // Recommendations
  if (path.startsWith('/recommendations')) {
    if (path.includes('/approve') || path.includes('/reject') || path.includes('/dismiss')) {
      return { id: 'mock', status: 'approved' };
    }
    if (path.includes('/generate')) {
      return { count: 3, message: 'Generated 3 new recommendations' };
    }
    const url = new URLSearchParams(path.split('?')[1] ?? '');
    return mockRecommendations({
      status: url.get('status') ?? undefined,
      category: url.get('category') ?? undefined,
      risk_level: url.get('risk_level') ?? undefined,
      page: parseInt(url.get('page') ?? '1', 10),
      size: parseInt(url.get('size') ?? '20', 10),
    });
  }

  // Resources
  if (path.startsWith('/resources')) return mockResources();

  // Ingestion
  if (path.startsWith('/ingestion/trigger')) {
    return { run_id: uuid(), status: 'started', message: 'Ingestion triggered successfully' };
  }
  if (path.startsWith('/ingestion/status')) {
    return {
      run_id: uuid(), status: 'completed', tenant_id: 'tenant-1',
      started_at: new Date(Date.now() - 120_000).toISOString(),
      completed_at: new Date().toISOString(),
      subscriptions_processed: 4, subscriptions_failed: 0,
    };
  }

  return null;
}
