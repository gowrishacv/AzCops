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
    <aside className="flex h-screen w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-6">
        <Shield className="h-6 w-6 text-primary mr-2" />
        <span className="text-lg font-bold">AzCops</span>
      </div>
      {/* Nav */}
      <nav className="flex-1 space-y-1 p-4">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      {/* User profile + version */}
      <div className="border-t p-4 space-y-3">
        <UserProfile />
        <p className="text-xs text-muted-foreground">AzCops Platform v0.1</p>
      </div>
    </aside>
  );
}
