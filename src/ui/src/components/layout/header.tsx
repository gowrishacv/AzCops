'use client';
import { Bell, ChevronRight, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HeaderProps { title: string; description?: string; }

export function Header({ title, description }: HeaderProps) {
  return (
    <div className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-border/50 bg-white/80 backdrop-blur-md px-6">
      <div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Dashboard</span>
          <ChevronRight className="h-3 w-3 text-muted-foreground/50" />
          <span className="font-medium">{title}</span>
        </div>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 rounded-lg border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground">
          <Search className="h-3.5 w-3.5" />
          <span className="text-xs">Search...</span>
          <kbd className="ml-4 rounded border bg-background px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            /
          </kbd>
        </div>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-blue-600" />
        </Button>
      </div>
    </div>
  );
}
