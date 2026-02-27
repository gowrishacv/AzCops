'use client';
import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HeaderProps { title: string; description?: string; }

export function Header({ title, description }: HeaderProps) {
  return (
    <div className="flex h-16 items-center justify-between border-b px-6">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon">
          <Bell className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}
