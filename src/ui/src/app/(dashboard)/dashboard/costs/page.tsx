'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { DollarSign } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Header } from '@/components/layout/header';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { costsApi } from '@/lib/api';
import { cn, formatCurrency, formatDate } from '@/lib/utils';

const PERIODS = [{ label: '7 days', value: 7 }, { label: '30 days', value: 30 }, { label: '90 days', value: 90 }];
const CHART_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#14b8a6', '#f97316', '#84cc16'];

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
/* Page                                                                */
/* ------------------------------------------------------------------ */
export default function CostsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ['costs', 'summary', days],
    queryFn: () => costsApi.summary(days),
  });

  const topServices = (data?.by_service ?? []).slice(0, 10);
  const total = data?.total_cost ?? 0;

  return (
    <div className="flex flex-col">
      <Header title="Cost Analysis" description="Breakdown of Azure spend by service and over time" />
      <div className="flex-1 p-6 space-y-6">
        {/* Period Selector */}
        <div className="inline-flex items-center rounded-full border bg-muted/50 p-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setDays(p.value)}
              className={cn(
                'rounded-full px-4 py-1.5 text-sm font-medium transition-all duration-200',
                days === p.value
                  ? 'bg-white text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Total Spend Summary */}
        <Card className="border-l-4 border-l-indigo-500 shadow-sm">
          <CardContent className="flex items-center justify-between py-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Spend ({days} days)</p>
              {isLoading ? (
                <Skeleton className="h-9 w-40 mt-1" />
              ) : (
                <p className="text-3xl font-bold tracking-tight">{formatCurrency(total)}</p>
              )}
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/10">
              <DollarSign className="h-6 w-6 text-indigo-500" />
            </div>
          </CardContent>
        </Card>

        {/* Cost by Service Bar Chart */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Cost by Service</CardTitle>
            <CardDescription>Top 10 Azure services by spend in the selected period</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-64 w-full" /> : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={topServices} layout="vertical" margin={{ left: 100 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                  <YAxis type="category" dataKey="service_name" tick={{ fontSize: 11 }} width={100} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0];
                      return (
                        <div className="rounded-lg border bg-card/95 backdrop-blur-sm p-3 shadow-xl">
                          <p className="text-xs text-muted-foreground mb-1">{d.payload?.service_name}</p>
                          <p className="text-sm font-semibold">{formatCurrency(d.value as number)}</p>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="total_cost" radius={[0, 4, 4, 0]}>
                    {topServices.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Daily Trend */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Daily Spend Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-48 w-full" /> : (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={data?.daily_trend ?? []}>
                  <defs>
                    <linearGradient id="grad2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="total_cost" stroke="#6366f1" fill="url(#grad2)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Service Table */}
        <Card className="shadow-sm">
          <CardHeader><CardTitle>Service Breakdown</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-48 w-full" /> : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Service</TableHead>
                    <TableHead className="text-right">Cost</TableHead>
                    <TableHead className="text-right">% of Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topServices.map((s) => {
                    const pct = total > 0 ? parseFloat(((s.total_cost / total) * 100).toFixed(1)) : 0;
                    return (
                      <TableRow key={s.service_name}>
                        <TableCell className="font-medium">{s.service_name}</TableCell>
                        <TableCell className="text-right">{formatCurrency(s.total_cost)}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                              <div
                                className="h-full rounded-full bg-indigo-500"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-muted-foreground w-12 text-right">{pct}%</span>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {topServices.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground py-8">No cost data available.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
