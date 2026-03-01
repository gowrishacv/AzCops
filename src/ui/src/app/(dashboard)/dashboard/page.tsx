'use client';
import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { DollarSign, Lightbulb, TrendingDown, TrendingUp, Server, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Header } from '@/components/layout/header';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { costsApi, recommendationsApi } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

const CHART_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

/* ------------------------------------------------------------------ */
/* Custom Recharts tooltip                                             */
/* ------------------------------------------------------------------ */
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-card/95 backdrop-blur-sm p-3 shadow-xl">
      <p className="text-xs text-muted-foreground mb-1">{label ? formatDate(label) : ''}</p>
      <p className="text-sm font-semibold">{formatCurrency(payload[0].value)}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* KPI Card                                                            */
/* ------------------------------------------------------------------ */
interface KpiCardProps {
  title: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  loading?: boolean;
  borderColor: string;
  iconBg: string;
  iconColor: string;
  trend?: 'up' | 'down';
}

function KpiCard({ title, value, sub, icon: Icon, loading, borderColor, iconBg, iconColor, trend }: KpiCardProps) {
  return (
    <Card className={`border-l-4 ${borderColor} shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconBg}`}>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-32" />
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold tracking-tight">{value}</span>
            {trend === 'down' && <TrendingDown className="h-4 w-4 text-emerald-500" />}
            {trend === 'up' && <TrendingUp className="h-4 w-4 text-red-500" />}
          </div>
        )}
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Risk-level helpers                                                  */
/* ------------------------------------------------------------------ */
const riskColor: Record<string, 'success' | 'warning' | 'destructive'> = {
  low: 'success', medium: 'warning', high: 'destructive',
};

const riskBorderColor: Record<string, string> = {
  low: 'border-l-emerald-500',
  medium: 'border-l-amber-500',
  high: 'border-l-red-500',
};

/* ------------------------------------------------------------------ */
/* Donut center label                                                  */
/* ------------------------------------------------------------------ */
function DonutCenterLabel({ total }: { total: number }) {
  return (
    <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="fill-foreground">
      <tspan x="50%" dy="-0.4em" className="text-lg font-bold">{formatCurrency(total)}</tspan>
      <tspan x="50%" dy="1.4em" className="text-xs fill-muted-foreground">Total</tspan>
    </text>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */
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
  const donutData = costData?.by_service?.slice(0, 6) ?? [];
  const donutTotal = donutData.reduce((s, d) => s + d.total_cost, 0);

  return (
    <div className="flex flex-col">
      <Header title="Overview" description="Azure Cost Optimization Dashboard" />
      <div className="flex-1 p-6 space-y-6">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Monthly Spend"
            value={formatCurrency(costData?.total_cost ?? 0)}
            sub={`Last ${costData?.period_days ?? 30} days`}
            icon={DollarSign}
            loading={costLoading}
            borderColor="border-l-indigo-500"
            iconBg="bg-indigo-500/10"
            iconColor="text-indigo-500"
            trend="up"
          />
          <KpiCard
            title="Potential Savings"
            value={formatCurrency(totalSavings)}
            sub="Per month if applied"
            icon={TrendingDown}
            loading={recsLoading}
            borderColor="border-l-emerald-500"
            iconBg="bg-emerald-500/10"
            iconColor="text-emerald-500"
            trend="down"
          />
          <KpiCard
            title="Open Recommendations"
            value={String(recsData?.total ?? 0)}
            sub="Awaiting review"
            icon={Lightbulb}
            loading={recsLoading}
            borderColor="border-l-amber-500"
            iconBg="bg-amber-500/10"
            iconColor="text-amber-500"
          />
          <KpiCard
            title="Resources Tracked"
            value="--"
            sub="Across all subscriptions"
            icon={Server}
            borderColor="border-l-purple-500"
            iconBg="bg-purple-500/10"
            iconColor="text-purple-500"
          />
        </div>

        {/* Charts: Area + Donut */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Area Chart */}
          <Card className="lg:col-span-2 shadow-sm">
            <CardHeader>
              <CardTitle>Cost Trend</CardTitle>
              <CardDescription>Daily spend over the last 30 days</CardDescription>
            </CardHeader>
            <CardContent>
              {costLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
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
                    <Tooltip content={<CustomTooltip />} />
                    <Area type="monotone" dataKey="total_cost" stroke="#6366f1" fill="url(#costGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Donut Chart */}
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Spend by Service</CardTitle>
              <CardDescription>Top 6 services</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              {costLoading ? (
                <Skeleton className="h-48 w-48 rounded-full" />
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={donutData}
                        dataKey="total_cost"
                        nameKey="service_name"
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        strokeWidth={0}
                      >
                        {donutData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        content={({ active, payload }) => {
                          if (!active || !payload?.length) return null;
                          const d = payload[0];
                          return (
                            <div className="rounded-lg border bg-card/95 backdrop-blur-sm p-3 shadow-xl">
                              <p className="text-xs text-muted-foreground mb-1">{d.name}</p>
                              <p className="text-sm font-semibold">{formatCurrency(d.value as number)}</p>
                            </div>
                          );
                        }}
                      />
                      <DonutCenterLabel total={donutTotal} />
                    </PieChart>
                  </ResponsiveContainer>

                  {/* Legend */}
                  <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1.5 w-full">
                    {donutData.map((s, i) => (
                      <div key={s.service_name} className="flex items-center gap-2 text-xs truncate">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
                        />
                        <span className="truncate text-muted-foreground">{s.service_name}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Top Recommendations */}
        <Card className="shadow-sm">
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
                  <div
                    key={rec.id}
                    className={`flex items-center justify-between rounded-lg border border-l-4 ${riskBorderColor[rec.risk_level] ?? 'border-l-muted'} p-3 hover:shadow-md hover:bg-accent/50 cursor-pointer group transition-all duration-200`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{rec.short_description}</p>
                      <p className="text-xs text-muted-foreground capitalize">{rec.category.replace('_', ' ')} &middot; {rec.rule_id}</p>
                    </div>
                    <div className="flex items-center gap-3 ml-4 shrink-0">
                      <Badge variant={riskColor[rec.risk_level] ?? 'secondary'}>{rec.risk_level}</Badge>
                      <span className="text-sm font-semibold text-emerald-600">{formatCurrency(rec.estimated_monthly_savings)}/mo</span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </div>
                ))}
                {recsData?.items.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-8">No open recommendations.</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
