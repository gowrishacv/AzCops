'use client';
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Server, Monitor, Database, HardDrive, Globe, Box, Lock, BarChart3, Zap, Search, Layers, FolderOpen,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Header } from '@/components/layout/header';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { apiFetch } from '@/lib/api';
import type { PaginatedResponse } from '@/lib/api';
import type { LucideIcon } from 'lucide-react';

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

function getResourceIcon(type: string): LucideIcon {
  if (type.includes('virtualMachines')) return Monitor;
  if (type.includes('Sql') || type.includes('DocumentDB')) return Database;
  if (type.includes('Storage') || type.includes('disks') || type.includes('snapshots')) return HardDrive;
  if (type.includes('Network') || type.includes('loadBalancers')) return Globe;
  if (type.includes('Web') || type.includes('sites')) return Globe;
  if (type.includes('ContainerService')) return Box;
  if (type.includes('KeyVault')) return Lock;
  if (type.includes('Insights') || type.includes('OperationalInsights')) return BarChart3;
  if (type.includes('Cache')) return Zap;
  return Server;
}

export default function ResourcesPage() {
  const { data, isLoading } = useResources();
  const [search, setSearch] = useState('');

  const items = data?.items ?? [];

  const uniqueTypes = useMemo(() => {
    const set = new Set(items.map((r) => r.type));
    return set.size;
  }, [items]);

  const uniqueResourceGroups = useMemo(() => {
    const set = new Set(items.map((r) => r.resource_group));
    return set.size;
  }, [items]);

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.type.toLowerCase().includes(q) ||
        r.resource_group.toLowerCase().includes(q)
    );
  }, [items, search]);

  return (
    <div className="flex flex-col">
      <Header title="Resources" description="Azure resources tracked across all subscriptions" />
      <div className="flex-1 p-6 space-y-4">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          {/* Total Resources */}
          <Card className="border-l-4 border-l-purple-500 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Resources</CardTitle>
              <Server className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold">{data?.total ?? 0}</div>
              )}
            </CardContent>
          </Card>

          {/* Resource Types */}
          <Card className="border-l-4 border-l-blue-500 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resource Types</CardTitle>
              <Layers className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold">{uniqueTypes}</div>
              )}
            </CardContent>
          </Card>

          {/* Resource Groups */}
          <Card className="border-l-4 border-l-emerald-500 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resource Groups</CardTitle>
              <FolderOpen className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold">{uniqueResourceGroups}</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Search bar */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search resources..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-lg border bg-background pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        {/* Resource Table */}
        <Card className="shadow-sm">
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
                  {filtered.map((r) => {
                    const Icon = getResourceIcon(r.type);
                    return (
                      <TableRow key={r.id}>
                        <TableCell className="font-medium font-mono text-xs">{r.name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                            <Badge variant="secondary" className="text-xs">
                              {resourceTypeLabel(r.type)}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">{r.resource_group}</TableCell>
                        <TableCell className="text-sm capitalize">{r.location}</TableCell>
                        <TableCell>
                          {r.tags && Object.keys(r.tags).length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {Object.entries(r.tags).slice(0, 3).map(([k, v]) => (
                                <span
                                  key={k}
                                  className="inline-flex items-center rounded-md bg-blue-50 border border-blue-100 px-1.5 py-0.5 text-[11px] text-blue-700"
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
                    );
                  })}
                  {filtered.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
                        {search.trim()
                          ? 'No resources match your search.'
                          : 'No resources found. Run an ingestion to populate resource data.'}
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
