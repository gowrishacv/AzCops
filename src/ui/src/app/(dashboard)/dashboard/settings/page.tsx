'use client';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { Header } from '@/components/layout/header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { healthApi } from '@/lib/api';

export default function SettingsPage() {
  const { data: health, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    retry: 1,
  });

  return (
    <div className="flex flex-col">
      <Header title="Settings" description="Platform configuration and connection status" />
      <div className="flex-1 p-6 space-y-4">

        {/* API Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>API Connection</CardTitle>
                <CardDescription>Status of the AzCops FastAPI backend</CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                disabled={isFetching}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              {isLoading ? (
                <Skeleton className="h-5 w-48" />
              ) : isError ? (
                <>
                  <XCircle className="h-5 w-5 text-red-500" />
                  <span className="text-sm font-medium text-red-600">API Unreachable</span>
                  <Badge variant="destructive">offline</Badge>
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span className="text-sm font-medium text-green-600">Connected</span>
                  <Badge variant="success">{health?.status}</Badge>
                </>
              )}
            </div>

            {health && (
              <div className="rounded-md bg-muted p-4 space-y-2">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">database: </span>
                  <span className="font-semibold">{health.database}</span>
                </p>
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">version:  </span>
                  <span className="font-semibold">{health.version}</span>
                </p>
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">api_url:  </span>
                  <span className="font-semibold">
                    {process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1'}
                  </span>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Azure Config */}
        <Card>
          <CardHeader>
            <CardTitle>Azure Configuration</CardTitle>
            <CardDescription>Entra ID application settings (read from environment)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-4 space-y-2">
              <p className="text-xs font-mono">
                <span className="text-muted-foreground">AZURE_CLIENT_ID:  </span>
                <span className="font-semibold">
                  {process.env.NEXT_PUBLIC_AZURE_CLIENT_ID
                    ? `${process.env.NEXT_PUBLIC_AZURE_CLIENT_ID.slice(0, 8)}…`
                    : <span className="text-yellow-600">not set</span>}
                </span>
              </p>
              <p className="text-xs font-mono">
                <span className="text-muted-foreground">AZURE_TENANT_ID:  </span>
                <span className="font-semibold">
                  {process.env.NEXT_PUBLIC_AZURE_TENANT_ID
                    ? `${process.env.NEXT_PUBLIC_AZURE_TENANT_ID.slice(0, 8)}…`
                    : <span className="text-yellow-600">not set</span>}
                </span>
              </p>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Set these in <code className="bg-muted px-1 rounded">.env.local</code> — see{' '}
              <code className="bg-muted px-1 rounded">.env.local.example</code> for the full template.
            </p>
          </CardContent>
        </Card>

        {/* Platform Info */}
        <Card>
          <CardHeader>
            <CardTitle>Platform</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-4 space-y-2">
              <p className="text-xs font-mono"><span className="text-muted-foreground">name:     </span><span>AzCops</span></p>
              <p className="text-xs font-mono"><span className="text-muted-foreground">version:  </span><span>0.1.0</span></p>
              <p className="text-xs font-mono"><span className="text-muted-foreground">ui_stack: </span><span>Next.js 14 · Tailwind · Recharts</span></p>
              <p className="text-xs font-mono"><span className="text-muted-foreground">api_stack:</span><span>FastAPI · PostgreSQL · SQLAlchemy</span></p>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
