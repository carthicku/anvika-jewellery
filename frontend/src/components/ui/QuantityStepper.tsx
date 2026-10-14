import { Minus, Plus } from 'lucide-react';

import { cn } from '@/lib/cn';

/**
 * − [n] + control. The value is announced through the group label; buttons disable at the limits
 * so customers can't request more than is available.
 */
export function QuantityStepper({
  value,
  min = 1,
  max,
  onChange,
  label,
  disabled = false,
  size = 'md',
}: {
  value: number;
  min?: number;
  max: number;
  onChange: (value: number) => void;
  label: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
}) {
  const button = cn(
    'inline-flex items-center justify-center text-ink transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:text-ink-subtle disabled:hover:bg-transparent',
    size === 'sm' ? 'size-9' : 'size-11',
  );
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex items-center rounded-sm border border-line-strong bg-surface"
    >
      <button
        type="button"
        className={button}
        onClick={() => {
          onChange(value - 1);
        }}
        disabled={disabled || value <= min}
        aria-label="Decrease quantity"
      >
        <Minus className="size-3.5" aria-hidden="true" />
      </button>
      <output
        aria-live="polite"
        aria-label={`Quantity ${value}`}
        className={cn('tabular min-w-8 text-center text-sm', disabled && 'text-ink-subtle')}
      >
        {value}
      </output>
      <button
        type="button"
        className={button}
        onClick={() => {
          onChange(value + 1);
        }}
        disabled={disabled || value >= max}
        aria-label="Increase quantity"
      >
        <Plus className="size-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}
