import type { Price as PriceData } from '@/api/types';
import { cn } from '@/lib/cn';
import { formatMoney, hasPaise } from '@/lib/format';

const UNAVAILABLE: Record<string, string> = {
  NO_GOLD_RATE: 'Price on request',
  MISSING_WEIGHT: 'Price on request',
  MISSING_FIXED_PRICE: 'Price on request',
  PURITY_MISMATCH: 'Price on request',
  NO_VARIANTS: 'Currently unavailable',
};

/**
 * Shows a backend-calculated price. Strike-through "compare at" prices get a visually hidden
 * "Original price" so screen readers announce them correctly. No arithmetic happens here.
 */
export function Price({
  price,
  size = 'md',
  className,
}: {
  price: PriceData;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  if (!price.available || !price.amount) {
    return (
      <p className={cn('text-sm text-ink-muted', className)}>
        {UNAVAILABLE[price.unavailable_reason ?? ''] ?? 'Price on request'}
      </p>
    );
  }
  const amountSize = { sm: 'text-sm', md: 'text-base', lg: 'text-2xl' }[size];
  const paise = hasPaise(price.amount) || hasPaise(price.compare_at);
  return (
    <p className={cn('tabular flex flex-wrap items-baseline gap-x-2', className)}>
      <span className={cn('font-medium text-ink', amountSize)}>
        {price.compare_at && <span className="sr-only">Offer price </span>}
        {formatMoney(price.amount, { paise })}
      </span>
      {price.compare_at && (
        <s className="text-sm text-ink-subtle">
          <span className="sr-only">Original price </span>
          {formatMoney(price.compare_at, { paise })}
        </s>
      )}
    </p>
  );
}
