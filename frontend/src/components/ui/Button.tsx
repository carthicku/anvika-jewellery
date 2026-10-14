import { Slot } from 'radix-ui';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { cn } from '@/lib/cn';

import { Spinner } from './Spinner';

type Variant = 'primary' | 'secondary' | 'ghost' | 'link' | 'danger';
type Size = 'sm' | 'md' | 'lg';

const base =
  'inline-flex items-center justify-center gap-2 rounded-sm font-medium tracking-wide transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 select-none';

const variants: Record<Variant, string> = {
  primary: 'bg-ink text-ivory hover:bg-ink/88 active:bg-ink',
  secondary: 'border border-ink/80 bg-transparent text-ink hover:bg-ink hover:text-ivory',
  ghost: 'text-ink hover:bg-surface-muted',
  link: 'h-auto px-0 text-ink underline decoration-gold underline-offset-4 hover:decoration-ink',
  danger: 'bg-danger text-white hover:bg-danger/90',
};

const sizes: Record<Size, string> = {
  sm: 'min-h-9 px-4 text-sm',
  md: 'min-h-11 px-6 text-sm',
  lg: 'min-h-13 px-8 text-base',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  /** Shows a spinner, keeps the width, disables the button and sets aria-busy. */
  loading?: boolean;
  /** Render the child element (e.g. a router <Link>) with button styling. */
  asChild?: boolean;
  children: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  asChild = false,
  className,
  disabled,
  children,
  type,
  ...props
}: ButtonProps) {
  const classes = cn(base, variants[variant], variant !== 'link' && sizes[size], className);
  if (asChild) {
    return (
      <Slot.Root className={classes} {...props}>
        {children}
      </Slot.Root>
    );
  }
  return (
    <button
      type={type ?? 'button'}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Spinner className="size-4" label="" />}
      {children}
    </button>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Accessible name — required because the button shows only an icon. */
  label: string;
  children: ReactNode;
}

export function IconButton({ label, className, children, type, ...props }: IconButtonProps) {
  return (
    <button
      type={type ?? 'button'}
      aria-label={label}
      title={label}
      className={cn(
        'relative inline-flex size-11 items-center justify-center rounded-sm text-ink transition-colors hover:bg-surface-muted disabled:opacity-50',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
