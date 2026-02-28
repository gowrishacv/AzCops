'use client';

import { useMsal } from '@azure/msal-react';
import { LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AUTH_ENABLED } from '@/lib/msal';

/**
 * Displays user avatar (initials), name, email, and a logout button.
 * In dev mode (AUTH_ENABLED=false), shows a "Dev User" placeholder.
 */
export function UserProfile() {
  const { instance, accounts } = useMsal();
  const account = accounts[0];

  // Dev bypass
  if (!AUTH_ENABLED) {
    return (
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
          D
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">Dev User</p>
          <p className="text-xs text-muted-foreground truncate">dev@localhost</p>
        </div>
      </div>
    );
  }

  if (!account) return null;

  const name = account.name ?? account.username ?? 'User';
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const handleLogout = () => {
    instance.logoutRedirect({ postLogoutRedirectUri: '/' });
  };

  return (
    <div className="flex items-center gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{name}</p>
        <p className="text-xs text-muted-foreground truncate">{account.username}</p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={handleLogout}
        title="Sign out"
        className="shrink-0"
      >
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  );
}
