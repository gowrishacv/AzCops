'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { InteractionStatus } from '@azure/msal-browser';
import { Shield } from 'lucide-react';
import { AUTH_ENABLED } from '@/lib/msal';

/**
 * Wraps protected routes. Redirects unauthenticated users to `/`.
 * When AUTH_ENABLED=false (dev mode), renders children unconditionally.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useIsAuthenticated();
  const { inProgress } = useMsal();
  const router = useRouter();

  useEffect(() => {
    if (!AUTH_ENABLED) return;
    if (inProgress !== InteractionStatus.None) return; // wait for MSAL
    if (!isAuthenticated) {
      router.replace('/');
    }
  }, [isAuthenticated, inProgress, router]);

  // Dev bypass — no auth check
  if (!AUTH_ENABLED) return <>{children}</>;

  // MSAL still initialising
  if (inProgress !== InteractionStatus.None) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Shield className="h-10 w-10 text-primary animate-pulse" />
          <p className="text-sm text-muted-foreground">Authenticating...</p>
        </div>
      </div>
    );
  }

  // Not authenticated — will redirect via useEffect
  if (!isAuthenticated) return null;

  return <>{children}</>;
}
