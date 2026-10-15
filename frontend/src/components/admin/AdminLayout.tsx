import {
  BadgePercent,
  ClipboardList,
  Coins,
  FileText,
  FolderTree,
  Gauge,
  Gem,
  History,
  Inbox,
  Menu,
  MessageSquareText,
  Package,
  Settings,
  ShieldCheck,
  Store,
  Truck,
  Undo2,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, NavLink, Outlet, useLocation } from 'react-router';

import { useLogout, useMe } from '@/api/queries/account';
import { PageMeta } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { DialogRoot, SheetContent } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  permission: string;
  end?: boolean;
}

/** Links are hidden when the role lacks the permission. This is convenience only — the backend
 * checks the permission on every request. */
const NAV: NavItem[] = [
  { to: '/admin', label: 'Dashboard', icon: Gauge, permission: 'dashboard:view', end: true },
  { to: '/admin/orders', label: 'Orders', icon: ClipboardList, permission: 'orders:write' },
  { to: '/admin/returns', label: 'Returns', icon: Undo2, permission: 'orders:write' },
  { to: '/admin/products', label: 'Products', icon: Gem, permission: 'catalogue:write' },
  {
    to: '/admin/categories',
    label: 'Categories & collections',
    icon: FolderTree,
    permission: 'catalogue:write',
  },
  { to: '/admin/inventory', label: 'Inventory', icon: Package, permission: 'inventory:write' },
  { to: '/admin/customers', label: 'Customers', icon: Users, permission: 'customers:view' },
  { to: '/admin/enquiries', label: 'Enquiries', icon: Inbox, permission: 'customers:view' },
  {
    to: '/admin/promotions',
    label: 'Discounts & coupons',
    icon: BadgePercent,
    permission: 'promotions:write',
  },
  { to: '/admin/gold-rates', label: 'Gold rates', icon: Coins, permission: 'pricing:write' },
  { to: '/admin/shipping', label: 'Delivery', icon: Truck, permission: 'settings:write' },
  { to: '/admin/reviews', label: 'Reviews', icon: MessageSquareText, permission: 'content:write' },
  { to: '/admin/content', label: 'Content pages', icon: FileText, permission: 'content:write' },
  { to: '/admin/settings', label: 'Settings', icon: Settings, permission: 'settings:write' },
  { to: '/admin/staff', label: 'Staff', icon: ShieldCheck, permission: 'users:manage' },
  { to: '/admin/audit', label: 'Audit log', icon: History, permission: 'audit:view' },
];

function Nav({ permissions, onNavigate }: { permissions: string[]; onNavigate?: () => void }) {
  return (
    <nav aria-label="Admin">
      <ul className="space-y-0.5">
        {NAV.filter((item) => permissions.includes(item.permission)).map(
          ({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-11 items-center gap-3 rounded-sm px-3 text-sm',
                    isActive ? 'bg-ink text-ivory' : 'text-ink hover:bg-surface-muted',
                  )
                }
              >
                <Icon className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />
                {label}
              </NavLink>
            </li>
          ),
        )}
      </ul>
      <Link
        to="/"
        className="mt-4 flex min-h-11 items-center gap-3 border-t border-line px-3 pt-4 text-sm text-ink-muted hover:text-ink"
      >
        <Store className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />
        View store
      </Link>
    </nav>
  );
}

/** Admin frame: top bar, permission-filtered side navigation, main content. */
export function AdminLayout() {
  const me = useMe();
  const logout = useLogout();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const previousPath = useRef(location.pathname);

  useEffect(() => {
    if (previousPath.current === location.pathname) return;
    previousPath.current = location.pathname;
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  if (me.isPending) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner />
      </div>
    );
  }
  const user = me.data;
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (user.role === 'customer' || user.permissions.length === 0) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center">
        <PageMeta title="Not available" path="/admin" noindex />
        <h1 className="font-display text-3xl">This area is for store staff</h1>
        <p className="text-ink-muted">Your account doesn’t have access to the store admin.</p>
        <Button asChild>
          <Link to="/">Go to the store</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-ivory">
      <PageMeta title="Admin" path="/admin" noindex />
      <a
        href="#admin-main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-sm focus:bg-ink focus:px-4 focus:py-2 focus:text-ivory"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface px-4">
        <DialogRoot open={menuOpen} onOpenChange={setMenuOpen}>
          <button
            type="button"
            className="inline-flex size-11 items-center justify-center rounded-sm hover:bg-surface-muted lg:hidden"
            aria-label="Open admin menu"
            onClick={() => {
              setMenuOpen(true);
            }}
          >
            <Menu className="size-5" aria-hidden="true" />
          </button>
          <SheetContent title="Admin menu">
            <div className="p-3">
              <Nav
                permissions={user.permissions}
                onNavigate={() => {
                  setMenuOpen(false);
                }}
              />
            </div>
          </SheetContent>
        </DialogRoot>
        <Link to="/admin" className="font-display text-xl tracking-[0.2em] uppercase">
          Anvika <span className="text-sm tracking-normal text-ink-muted normal-case">admin</span>
        </Link>
        <div className="ml-auto flex items-center gap-1 text-sm whitespace-nowrap sm:gap-2">
          <span className="hidden text-ink-muted sm:inline">
            {user.full_name} · {user.role}
          </span>
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link to="/">View store</Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            loading={logout.isPending}
            onClick={() => {
              logout.mutate({ redirectTo: '/login' });
            }}
          >
            Sign out
          </Button>
        </div>
      </header>
      <div className="flex flex-1">
        <aside className="hidden w-64 shrink-0 border-r border-line bg-surface p-3 lg:block">
          <Nav permissions={user.permissions} />
        </aside>
        <main
          id="admin-main"
          ref={mainRef}
          tabIndex={-1}
          className="min-w-0 flex-1 px-4 py-6 outline-none sm:px-8 sm:py-8"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
