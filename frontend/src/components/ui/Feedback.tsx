import { AlertTriangle, CheckCircle2, Info, XCircle, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

import { ApiError } from '@/api/client';
import { cn } from '@/lib/cn';

import { Button } from './Button';

type Tone = 'neutral' | 'gold' | 'success' | 'warning' | 'danger' | 'info';

const badgeTones: Record<Tone, string> = {
  neutral: 'bg-surface-muted text-ink-muted',
  gold: 'bg-gold-soft text-gold-deep',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  info: 'bg-info-soft text-info',
};

/** Small label. Always contains text — colour alone never carries meaning. */
export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium tracking-wide',
        badgeTones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const alertConfig: Record<Exclude<Tone, 'neutral' | 'gold'>, { icon: LucideIcon; cls: string }> = {
  success: { icon: CheckCircle2, cls: 'border-success/30 bg-success-soft text-success' },
  warning: { icon: AlertTriangle, cls: 'border-warning/30 bg-warning-soft text-warning' },
  danger: { icon: XCircle, cls: 'border-danger/30 bg-danger-soft text-danger' },
  info: { icon: Info, cls: 'border-info/30 bg-info-soft text-info' },
};

/** Inline message. Errors use role="alert"; others are polite status updates. */
export function Alert({
  tone = 'info',
  title,
  children,
  className,
}: {
  tone?: keyof typeof alertConfig;
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  const { icon: Icon, cls } = alertConfig[tone];
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cn('flex gap-3 rounded-md border px-4 py-3 text-sm', cls, className)}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-1 text-ink">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-ink-muted">{children}</div>}
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'animate-pulse rounded-sm bg-surface-muted motion-reduce:animate-none',
        className,
      )}
    />
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('mx-auto max-w-md py-16 text-center', className)}>
      {Icon && <Icon className="mx-auto size-8 text-gold" strokeWidth={1.25} aria-hidden="true" />}
      <h2 className="mt-4 font-display text-2xl font-medium">{title}</h2>
      {children && <div className="mt-2 text-ink-muted">{children}</div>}
      {action && <div className="mt-6 flex justify-center gap-3">{action}</div>}
    </div>
  );
}

/** Data-loading failure with a retry action. Shows the support reference when available. */
export function ErrorState({
  error,
  onRetry,
  title = 'We couldn’t load this',
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
  className?: string;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const message =
    apiError?.code === 'NETWORK_ERROR'
      ? 'Please check your internet connection and try again.'
      : (apiError?.message ?? 'Something went wrong. Please try again.');
  return (
    <div role="alert" className={cn('mx-auto max-w-md py-16 text-center', className)}>
      <XCircle className="mx-auto size-8 text-danger" strokeWidth={1.25} aria-hidden="true" />
      <h2 className="mt-4 font-display text-2xl font-medium">{title}</h2>
      <p className="mt-2 text-ink-muted">{message}</p>
      {apiError?.requestId && (
        <p className="mt-2 text-xs text-ink-subtle">Reference: {apiError.requestId.slice(0, 8)}</p>
      )}
      {onRetry && (
        <Button variant="secondary" className="mt-6" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
