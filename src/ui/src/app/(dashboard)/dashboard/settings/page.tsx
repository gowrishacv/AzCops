'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle, XCircle, RefreshCw, Copy, Check } from 'lucide-react';
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

  const [copied, setCopied] = useState('');
  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(''), 2000);
  };

  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
  const clientId = process.env.NEXT_PUBLIC_AZURE_CLIENT_ID;
  const tenantId = process.env.NEXT_PUBLIC_AZURE_TENANT_ID;

  return (
    <div className="flex flex-col">
      <Header title="Settings" description="Platform configuration and connection status" />
      <div className="flex-1 p-6 space-y-4">

        {/* API Status */}
        <Card className="shadow-sm hover:shadow-md transition-shadow">
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
                  <div className="relative">
                    <div className="h-3 w-3 rounded-full bg-red-500" />
                  </div>
                  <XCircle className="h-5 w-5 text-red-500" />
                  <span className="text-sm font-medium text-red-600">API Unreachable</span>
                  <Badge variant="destructive">offline</Badge>
                </>
              ) : (
                <>
                  <div className="relative">
                    <div className="h-3 w-3 rounded-full bg-green-500" />
                    <div className="absolute inset-0 h-3 w-3 rounded-full bg-green-500 animate-ping opacity-20" />
                  </div>
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span className="text-sm font-medium text-green-600">Connected</span>
                  <Badge variant="success">{health?.status}</Badge>
                </>
              )}
            </div>

            {health && (
              <div className="rounded-md bg-muted p-4 space-y-2">
                <div className="flex items-center justify-between group">
                  <p className="text-xs font-mono">
                    <span className="text-muted-foreground">database: </span>
                    <span className="font-semibold">{health.database}</span>
                  </p>
                  <button
                    onClick={() => copyToClipboard(health.database, 'database')}
                    className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                    title="Copy to clipboard"
                  >
                    {copied === 'database' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                  </button>
                </div>
                <div className="flex items-center justify-between group">
                  <p className="text-xs font-mono">
                    <span className="text-muted-foreground">version:  </span>
                    <span className="font-semibold">{health.version}</span>
                  </p>
                  <button
                    onClick={() => copyToClipboard(health.version, 'version')}
                    className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                    title="Copy to clipboard"
                  >
                    {copied === 'version' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                  </button>
                </div>
                <div className="flex items-center justify-between group">
                  <p className="text-xs font-mono">
                    <span className="text-muted-foreground">api_url:  </span>
                    <span className="font-semibold">{apiUrl}</span>
                  </p>
                  <button
                    onClick={() => copyToClipboard(apiUrl, 'api_url')}
                    className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                    title="Copy to clipboard"
                  >
                    {copied === 'api_url' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                  </button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Azure Config */}
        <Card className="shadow-sm hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle>Azure Configuration</CardTitle>
            <CardDescription>Entra ID application settings (read from environment)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-4 space-y-2">
              <div className="flex items-center justify-between group">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">AZURE_CLIENT_ID:  </span>
                  <span className="font-semibold">
                    {clientId
                      ? `${clientId.slice(0, 8)}…`
                      : <span className="text-yellow-600">not set</span>}
                  </span>
                </p>
                {clientId && (
                  <button
                    onClick={() => copyToClipboard(clientId, 'client_id')}
                    className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                    title="Copy to clipboard"
                  >
                    {copied === 'client_id' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                  </button>
                )}
              </div>
              <div className="flex items-center justify-between group">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">AZURE_TENANT_ID:  </span>
                  <span className="font-semibold">
                    {tenantId
                      ? `${tenantId.slice(0, 8)}…`
                      : <span className="text-yellow-600">not set</span>}
                  </span>
                </p>
                {tenantId && (
                  <button
                    onClick={() => copyToClipboard(tenantId, 'tenant_id')}
                    className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                    title="Copy to clipboard"
                  >
                    {copied === 'tenant_id' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                  </button>
                )}
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Set these in <code className="bg-muted px-1 rounded">.env.local</code> — see{' '}
              <code className="bg-muted px-1 rounded">.env.local.example</code> for the full template.
            </p>
          </CardContent>
        </Card>

        {/* Platform Info */}
        <Card className="shadow-sm hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle>Platform</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-4 space-y-2">
              <div className="flex items-center justify-between group">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">name:     </span>
                  <span className="font-semibold">AzCops</span>
                </p>
                <button
                  onClick={() => copyToClipboard('AzCops', 'name')}
                  className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                  title="Copy to clipboard"
                >
                  {copied === 'name' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                </button>
              </div>
              <div className="flex items-center justify-between group">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">version:  </span>
                  <span className="font-semibold">0.1.0</span>
                </p>
                <button
                  onClick={() => copyToClipboard('0.1.0', 'platform_version')}
                  className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                  title="Copy to clipboard"
                >
                  {copied === 'platform_version' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                </button>
              </div>
              <div className="flex items-center justify-between group">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">ui_stack: </span>
                  <span className="font-semibold">Next.js 14 · Tailwind · Recharts</span>
                </p>
                <button
                  onClick={() => copyToClipboard('Next.js 14 · Tailwind · Recharts', 'ui_stack')}
                  className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                  title="Copy to clipboard"
                >
                  {copied === 'ui_stack' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                </button>
              </div>
              <div className="flex items-center justify-between group">
                <p className="text-xs font-mono">
                  <span className="text-muted-foreground">api_stack:</span>
                  <span className="font-semibold">FastAPI · PostgreSQL · SQLAlchemy</span>
                </p>
                <button
                  onClick={() => copyToClipboard('FastAPI · PostgreSQL · SQLAlchemy', 'api_stack')}
                  className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                  title="Copy to clipboard"
                >
                  {copied === 'api_stack' ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
