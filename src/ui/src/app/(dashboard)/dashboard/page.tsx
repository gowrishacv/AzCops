'use client';
import { useQuery } from '@tanstack/react-query';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { DollarSign, Lightbulb, TrendingDown, Server } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Header } from '@/components/layout/header';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { costsApi, recommendationsApi } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

function KpiCard({ title, value, sub, icon: Icon, loading }: { title: string; value: string; sub?: string; icon: React.ElementType; loading?: boolean }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-8 w-32" /> : <div className="text-2xl font-bold">{value}</div>}
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

const riskColor: Record<string, 'success' | 'warning' | 'destructive'> = {
  low: 'success', medium: 'warning', high: 'destructive',
};

export default function DashboardPage() {
  const { data: costData, isLoading: costLoading } = useQuery({
    queryKey: ['costs', 'summary', 30],
    queryFn: () => costsApi.summary(30),
  });

  const { data: recsData, isLoading: recsLoading } = useQuery({
    queryKey: ['recommendations', 'open'],
    queryFn: () => recommendationsApi.list({ status: 'open', size: 5 }),
  });

  const totalSavings = recsData?.items.reduce((s, r) => s + r.estimated_monthly_savings, 0) ?? 0;

  return (
    <div className="flex flex-col">
      <Header title="Overview" description="Azure Cost Optimization Dashboard" />
      <div className="flex-1 p-6 space-y-6">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <KpiCard title="Monthly Spend" value={formatCurrency(costData?.total_cost ?? 0)} sub={`Last ${costData?.period_days ?? 30} days`} icon={DollarSign} loading={costLoading} />
          <KpiCard title="Potential Savings" value={formatCurrency(totalSavings)} sub="Per month if applied" icon={TrendingDown} loading={recsLoading} />
          <KpiCard title="Open Recommendations" value={String(recsData?.total ?? 0)} sub="Awaiting review" icon={Lightbulb} loading={recsLoading} />
          <KpiCard title="Resources Tracked" value="—" sub="Across all subscriptions" icon={Server} />
        </div>

        {/* Cost Trend */}
        <Card>
          <CardHeader>
            <CardTitle>Cost Trend</CardTitle>
            <CardDescription>Daily spend over the last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            {costLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={costData?.daily_trend ?? []}>
                  <defs>
                    <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                  <Tooltip formatter={(v: number) => [formatCurrency(v), 'Cost']} labelFormatter={(l: string) => formatDate(l)} />
                  <Area type="monotone" dataKey="total_cost" stroke="#6366f1" fill="url(#costGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Top Recommendations */}
        <Card>
          <CardHeader>
            <CardTitle>Top Savings Opportunities</CardTitle>
            <CardDescription>Highest priority open recommendations</CardDescription>
          </CardHeader>
          <CardContent>
            {recsLoading ? (
              <div className="space-y-3">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
            ) : (
              <div className="space-y-2">
                {recsData?.items.map((rec) => (
                  <div key={rec.id} className="flex items-center justify-between rounded-md border p-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{rec.short_description}</p>
                      <p className="text-xs text-muted-foreground capitalize">{rec.category.replace('_', ' ')} · {rec.rule_id}</p>
                    </div>
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <Badge variant={riskColor[rec.risk_level] ?? 'secondary'}>{rec.risk_level}</Badge>
                      <span className="text-sm font-semibold text-green-600">{formatCurrency(rec.estimated_monthly_savings)}/mo</span>
                    </div>
                  </div>
                ))}
                {recsData?.items.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">No open recommendations.</p>}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
