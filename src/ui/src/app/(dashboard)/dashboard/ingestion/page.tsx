'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Download, Play, RefreshCw, Zap, Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Header } from '@/components/layout/header';
import { recommendationsApi } from '@/lib/api';

/* ---------- status badge helper ---------- */
const statusConfig: Record<string, { variant: 'default' | 'success' | 'destructive' | 'warning' | 'secondary'; icon: React.ElementType }> = {
  running: { variant: 'warning', icon: RefreshCw },
  completed: { variant: 'success', icon: CheckCircle },
  failed: { variant: 'destructive', icon: XCircle },
  pending: { variant: 'secondary', icon: Clock },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = statusConfig[status] ?? statusConfig.pending;
  const Icon = cfg.icon;
  return (
    <Badge variant={cfg.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {status}
    </Badge>
  );
}

/* ---------- log entry type ---------- */
interface LogEntry {
  id: string;
  action: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message: string;
  timestamp: Date;
}

/* ---------- page ---------- */
export default function IngestionPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = (action: string, status: LogEntry['status'], message: string) => {
    setLogs((prev) => [
      { id: `${Date.now()}-${Math.random()}`, action, status, message, timestamp: new Date() },
      ...prev,
    ]);
  };

  const updateLastLog = (status: LogEntry['status'], message: string) => {
    setLogs((prev) => {
      if (prev.length === 0) return prev;
      const [first, ...rest] = prev;
      return [{ ...first, status, message }, ...rest];
    });
  };

  /* ── Rule Engine mutation ─────────────────── */
  const generateMutation = useMutation({
    mutationFn: () => recommendationsApi.generate(),
    onMutate: () => {
      addLog('Rule Engine', 'running', 'Running 11 optimization rules...');
    },
    onSuccess: (data) => {
      updateLastLog('completed', `Generated ${data.count} new recommendations`);
    },
    onError: (err: Error) => {
      updateLastLog('failed', err.message);
    },
  });

  return (
    <div className="flex flex-col">
      <Header title="Ingestion & Rules" description="Manage data ingestion and rule engine runs" />

      <div className="flex-1 p-6 space-y-6">
        {/* ── Action Cards ────────────────────── */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Data Ingestion */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary" />
                Data Ingestion
              </CardTitle>
              <CardDescription>
                Pull latest resources, costs, and Azure Advisor recommendations from your
                Azure subscriptions into the platform.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border bg-muted/50 p-4 text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-2">Connectors:</p>
                <ul className="space-y-1 ml-4 list-disc">
                  <li>Resource Graph — discovers all Azure resources</li>
                  <li>Cost Management — daily cost data by service/RG</li>
                  <li>Azure Advisor — cost optimization recommendations</li>
                  <li>Azure Monitor — VM CPU/memory utilization metrics</li>
                </ul>
              </div>
              <Button
                className="w-full"
                variant="outline"
                disabled
              >
                <Play className="mr-2 h-4 w-4" />
                Trigger Ingestion
                <Badge variant="secondary" className="ml-2 text-xs">
                  Requires Azure Infra
                </Badge>
              </Button>
              <p className="text-xs text-muted-foreground">
                Ingestion requires active Azure infrastructure. Run{' '}
                <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">terraform apply</code>{' '}
                to provision resources first.
              </p>
            </CardContent>
          </Card>

          {/* Rule Engine */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                Rule Engine
              </CardTitle>
              <CardDescription>
                Run optimization rules against ingested data to generate savings
                recommendations.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border bg-muted/50 p-4 text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-2">11 Rules across 4 categories:</p>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div>
                    <Badge variant="secondary" className="mb-1">Waste Detection</Badge>
                    <p className="text-xs ml-1">Disks, IPs, NICs, Snapshots</p>
                  </div>
                  <div>
                    <Badge variant="secondary" className="mb-1">Right-Sizing</Badge>
                    <p className="text-xs ml-1">VMs, App Services, SQL</p>
                  </div>
                  <div>
                    <Badge variant="secondary" className="mb-1">Rate Optimization</Badge>
                    <p className="text-xs ml-1">RIs, Savings Plans</p>
                  </div>
                  <div>
                    <Badge variant="secondary" className="mb-1">Governance</Badge>
                    <p className="text-xs ml-1">Tags, Budgets</p>
                  </div>
                </div>
              </div>
              <Button
                className="w-full"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
              >
                {generateMutation.isPending ? (
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="mr-2 h-4 w-4" />
                )}
                {generateMutation.isPending ? 'Running Rules...' : 'Run Rule Engine'}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* ── Activity Log ────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              Activity Log
            </CardTitle>
            <CardDescription>Recent ingestion and rule engine activity</CardDescription>
          </CardHeader>
          <CardContent>
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <AlertTriangle className="h-8 w-8 text-muted-foreground/50 mb-3" />
                <p className="text-sm text-muted-foreground">No activity yet.</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Run the rule engine or trigger an ingestion to see activity here.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className="flex items-start gap-3 rounded-lg border p-3"
                  >
                    <StatusBadge status={log.status} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{log.action}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{log.message}</p>
                    </div>
                    <time className="text-xs text-muted-foreground shrink-0">
                      {log.timestamp.toLocaleTimeString()}
                    </time>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
