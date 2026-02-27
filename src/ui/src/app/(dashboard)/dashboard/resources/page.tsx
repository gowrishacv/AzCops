'use client';
import { useQuery } from '@tanstack/react-query';
import { Server } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Header } from '@/components/layout/header';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { apiFetch } from '@/lib/api';
import type { PaginatedResponse } from '@/lib/api';

interface Resource {
  id: string;
  name: string;
  type: string;
  resource_group: string;
  location: string;
  tags: Record<string, string> | null;
}

function useResources() {
  return useQuery({
    queryKey: ['resources'],
    queryFn: () => apiFetch<PaginatedResponse<Resource>>('/resources?size=50'),
  });
}

function resourceTypeLabel(type: string): string {
  const parts = type.split('/');
  return parts[parts.length - 1] ?? type;
}

export default function ResourcesPage() {
  const { data, isLoading } = useResources();

  return (
    <div className="flex flex-col">
      <Header title="Resources" description="Azure resources tracked across all subscriptions" />
      <div className="flex-1 p-6 space-y-4">
        {/* Summary */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Resources</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading
                ? <Skeleton className="h-8 w-16" />
                : <div className="text-2xl font-bold">{data?.total ?? 0}</div>
              }
            </CardContent>
          </Card>
        </div>

        {/* Resource Table */}
        <Card>
          <CardHeader>
            <CardTitle>Resource Inventory</CardTitle>
            <CardDescription>
              All Azure resources collected via Resource Graph ingestion
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Resource Group</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Tags</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium font-mono text-xs">{r.name}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {resourceTypeLabel(r.type)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{r.resource_group}</TableCell>
                      <TableCell className="text-sm capitalize">{r.location}</TableCell>
                      <TableCell>
                        {r.tags && Object.keys(r.tags).length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(r.tags).slice(0, 3).map(([k, v]) => (
                              <span
                                key={k}
                                className="inline-flex items-center rounded px-1.5 py-0.5 text-xs bg-muted text-muted-foreground"
                              >
                                {k}: {v}
                              </span>
                            ))}
                            {Object.keys(r.tags).length > 3 && (
                              <span className="text-xs text-muted-foreground">+{Object.keys(r.tags).length - 3} more</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">No tags</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {data?.items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
                        No resources found. Run an ingestion to populate resource data.
                      </TableCell>
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
