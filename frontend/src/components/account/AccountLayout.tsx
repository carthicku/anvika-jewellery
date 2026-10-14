import { Heart, LogOut, MapPin, ShieldCheck, User, UserRound } from 'lucide-react';
import { Navigate, NavLink, Outlet, useLocation } from 'react-router';

import { useLogout, useMe, useResendVerification } from '@/api/queries/account';
import { Container } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Alert, Skeleton } from '@/components/ui/Feedback';
import { useToast } from '@/components/ui/Toaster';
import { cn } from '@/lib/cn';
import { errorMessage } from '@/lib/forms';

const NAV = [
  { to: '/account', label: 'Overview', icon: UserRound, end: true },
  { to: '/account/profile', label: 'Profile', icon: User },
  { to: '/account/addresses', label: 'Addresses', icon: MapPin },
  { to: '/account/wishlist', label: 'Wishlist', icon: Heart },
  { to: '/account/security', label: 'Sign-in & security', icon: ShieldCheck },
];

/**
 * Guards /account/* (sends guests to sign-in with a safe return path) and provides the account
 * navigation. The backend enforces access regardless — this only improves the experience.
 */
export function AccountLayout() {
  const me = useMe();
  const location = useLocation();
  const logout = useLogout();
  const resend = useResendVerification();
  const { notify } = useToast();

  if (me.isPending) {
    return (
      <Container className="py-16">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="mt-8 h-40 w-full" />
      </Container>
    );
  }
  if (!me.data) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  const user = me.data;

  const signOut = () => {
    logout.mutate(
      { redirectTo: '/' },
      {
        onSettled: () => {
          notify('You have been signed out.', 'info');
        },
      },
    );
  };

  return (
    <Container className="pt-10 pb-20">
      <p className="eyebrow">My account</p>
      <h1 className="mt-2 font-display text-4xl font-medium">
        Hello, {user.full_name.split(' ')[0]}
      </h1>

      {!user.email_verified && (
        <Alert tone="info" title="Please confirm your email address" className="mt-6">
          We sent a link to {user.email}.{' '}
          <button
            type="button"
            className="font-medium text-ink underline underline-offset-4"
            disabled={resend.isPending}
            onClick={() => {
              resend.mutate(undefined, {
                onSuccess: (data) => {
                  notify(data.message ?? 'Link sent.');
                },
                onError: (error) => {
                  notify(errorMessage(error), 'error');
                },
              });
            }}
          >
            Send a new link
          </button>
        </Alert>
      )}

      <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[14rem_1fr]">
        {/* min-w-0: let the menu scroll sideways on phones instead of widening the page */}
        <nav aria-label="Account" className="min-w-0">
          <ul className="flex gap-1 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <li key={to} className="shrink-0">
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      'flex min-h-11 items-center gap-3 rounded-sm px-3 text-sm transition-colors',
                      isActive
                        ? 'bg-surface font-medium text-ink shadow-soft'
                        : 'text-ink-muted hover:text-ink',
                    )
                  }
                >
                  <Icon className="size-4" strokeWidth={1.5} aria-hidden="true" />
                  {label}
                </NavLink>
              </li>
            ))}
            <li className="shrink-0 lg:mt-4 lg:border-t lg:border-line lg:pt-4">
              <Button
                variant="ghost"
                className="w-full justify-start px-3 font-normal text-ink-muted"
                onClick={signOut}
                loading={logout.isPending}
              >
                <LogOut className="size-4" strokeWidth={1.5} aria-hidden="true" />
                Sign out
              </Button>
            </li>
          </ul>
        </nav>
        <div className="min-w-0">
          <Outlet />
        </div>
      </div>
    </Container>
  );
}

export function AccountSection({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
        <div>
          <h2 className="font-display text-3xl">{title}</h2>
          {description && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
