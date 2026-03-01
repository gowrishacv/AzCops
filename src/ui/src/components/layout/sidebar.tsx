'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart3, DollarSign, Download, Lightbulb, Server, Settings, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { UserProfile } from '@/components/auth/user-profile';

const nav = [
  { href: '/dashboard', label: 'Overview', icon: BarChart3 },
  { href: '/dashboard/costs', label: 'Cost Analysis', icon: DollarSign },
  { href: '/dashboard/recommendations', label: 'Recommendations', icon: Lightbulb },
  { href: '/dashboard/resources', label: 'Resources', icon: Server },
  { href: '/dashboard/ingestion', label: 'Ingestion', icon: Download },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border/50 bg-gradient-to-b from-slate-50 to-white">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-border/50 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 shadow-lg shadow-blue-500/25">
          <Shield className="h-4 w-4 text-white" />
        </div>
        <span className="ml-2.5 text-lg font-bold tracking-tight">AzCops</span>
        <span className="ml-2 inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">
          v0.1
        </span>
      </div>
      {/* Nav */}
      <nav className="flex-1 space-y-1 p-4">
        {nav.map(({ href, label, icon: Icon }) => {
          const active =
            href === '/dashboard'
              ? pathname === '/dashboard'
              : pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                active
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/25'
                  : 'text-muted-foreground hover:bg-accent/80 hover:text-foreground hover:translate-x-0.5',
              )}
            >
              <Icon className={cn('h-4 w-4', active && 'drop-shadow-sm')} />
              {label}
              {active && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white/80" />
              )}
            </Link>
          );
        })}
      </nav>
      {/* User profile + version */}
      <div className="border-t border-border/50 p-4 space-y-3">
        <UserProfile />
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse-soft" />
          AzCops Platform v0.1
        </div>
      </div>
    </aside>
  );
}
