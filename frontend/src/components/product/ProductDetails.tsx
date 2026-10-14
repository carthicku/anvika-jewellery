import { CheckCircle2, CircleAlert, MapPin, XCircle } from 'lucide-react';
import { useId, useState, type SyntheticEvent } from 'react';

import { ApiError } from '@/api/client';
import { usePincodeCheck } from '@/api/queries/catalogue';
import type { Price, ProductDetail, StockStatus, Variant } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';
import {
  formatDateTime,
  formatMoney,
  hasPaise,
  formatShortDate,
  formatWeight,
  METAL_COLOUR_LABELS,
} from '@/lib/format';

/** Size / length options as an accessible radio group. Sold-out sizes stay visible but disabled. */
export function VariantPicker({
  variants,
  selectedId,
  onSelect,
}: {
  variants: Variant[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const id = useId();
  if (variants.length <= 1) return null;
  const hasSizes = variants.some((v) => v.size);
  return (
    <fieldset>
      <legend className="text-sm font-medium">{hasSizes ? 'Size' : 'Option'}</legend>
      <div className="mt-3 flex flex-wrap gap-2">
        {variants.map((variant) => {
          const soldOut = variant.stock_status === 'out_of_stock';
          const checked = variant.id === selectedId;
          return (
            <label
              key={variant.id}
              className={cn(
                'relative inline-flex min-h-11 min-w-14 cursor-pointer items-center justify-center rounded-sm border px-4 text-sm transition-colors has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus',
                checked ? 'border-ink bg-ink text-ivory' : 'border-line-strong hover:border-ink',
                soldOut && !checked && 'text-ink-subtle line-through decoration-ink-subtle',
              )}
            >
              <input
                type="radio"
                name={`${id}-variant`}
                value={variant.id}
                checked={checked}
                onChange={() => {
                  onSelect(variant.id);
                }}
                className="sr-only"
              />
              {variant.size ?? variant.label}
              {soldOut && <span className="sr-only"> (sold out)</span>}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function StockStatusLine({ status, quantity }: { status: StockStatus; quantity: number }) {
  if (status === 'out_of_stock') {
    return (
      <p className="flex items-center gap-2 text-sm text-danger">
        <XCircle className="size-4" aria-hidden="true" /> Out of stock
      </p>
    );
  }
  if (status === 'low_stock') {
    return (
      <p className="flex items-center gap-2 text-sm text-warning">
        <CircleAlert className="size-4" aria-hidden="true" />
        {quantity === 1 ? 'Only 1 left' : `Only ${quantity} left`}
      </p>
    );
  }
  return (
    <p className="flex items-center gap-2 text-sm text-success">
      <CheckCircle2 className="size-4" aria-hidden="true" /> In stock
    </p>
  );
}

/** The backend's itemised breakdown, rendered as-is (no arithmetic here). */
export function PriceBreakdown({ price }: { price: Price }) {
  if (!price.available) {
    return (
      <p className="text-sm text-ink-muted">
        A price can’t be shown for this piece right now. Please contact us for details.
      </p>
    );
  }
  const rows = price.breakdown;
  const paise = rows.some((row) => hasPaise(row.amount));
  return (
    <div>
      <table className="w-full text-sm">
        <caption className="sr-only">Price breakdown</caption>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.key}
              className={cn(row.key === 'total' && 'border-t border-line font-medium text-ink')}
            >
              <th scope="row" className="py-1.5 text-left font-normal">
                {row.key === 'total' ? 'Total (incl. GST)' : row.label}
              </th>
              <td className="tabular py-1.5 text-right">
                {row.amount.startsWith('-')
                  ? `− ${formatMoney(row.amount.slice(1), { paise })}`
                  : formatMoney(row.amount, { paise })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {price.gold_rate && (
        <p className="mt-3 text-xs text-ink-subtle">
          Gold rate used: {formatMoney(price.gold_rate.rate_per_gram)} per gram (
          {price.gold_rate.purity}), effective {formatDateTime(price.gold_rate.effective_from)}.
          Prices update when the rate changes; you’ll always confirm the final price before paying.
        </p>
      )}
    </div>
  );
}

export function SpecList({ product, variant }: { product: ProductDetail; variant: Variant }) {
  const rows: [string, string][] = [
    ['Purity', product.purity],
    ['Metal', METAL_COLOUR_LABELS[product.metal_colour] ?? product.metal_colour],
    ['SKU', variant.sku],
  ];
  if (variant.size) rows.push(['Size', variant.size]);
  if (variant.gross_weight_g) rows.push(['Gross weight', formatWeight(variant.gross_weight_g)]);
  if (variant.net_gold_weight_g)
    rows.push(['Net gold weight', formatWeight(variant.net_gold_weight_g)]);
  if (variant.stone_weight_ct)
    rows.push(['Stone weight', formatWeight(variant.stone_weight_ct, 'ct')]);
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
      {rows.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-ink-subtle">{term}</dt>
          <dd className="text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function PincodeChecker() {
  const id = useId();
  const [value, setValue] = useState('');
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const check = usePincodeCheck(submitted);

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    if (!/^[1-9][0-9]{5}$/.test(value)) {
      setLocalError('Enter a valid 6-digit PIN code.');
      return;
    }
    setLocalError(null);
    setSubmitted(value);
  };

  const serverError =
    check.error instanceof ApiError
      ? (check.error.fieldErrors.pincode ?? check.error.message)
      : null;
  const error = localError ?? serverError;

  return (
    <div>
      <form onSubmit={submit} className="flex gap-2" noValidate>
        <div className="relative flex-1">
          <label htmlFor={id} className="sr-only">
            Delivery PIN code
          </label>
          <MapPin
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-muted"
            aria-hidden="true"
          />
          <input
            id={id}
            inputMode="numeric"
            autoComplete="postal-code"
            maxLength={6}
            placeholder="Enter PIN code"
            value={value}
            onChange={(e) => {
              setValue(e.target.value.replace(/\D/g, ''));
            }}
            aria-invalid={error ? true : undefined}
            aria-describedby={`${id}-result`}
            className="min-h-11 w-full rounded-sm border border-line-strong bg-surface pr-3 pl-9 text-sm"
          />
        </div>
        <Button type="submit" variant="secondary" loading={check.isFetching}>
          Check
        </Button>
      </form>
      <div id={`${id}-result`} aria-live="polite" className="mt-3 text-sm">
        {error && <p className="text-danger">{error}</p>}
        {!error && check.isFetching && <Spinner label="Checking delivery" />}
        {!error && check.data && !check.data.serviceable && (
          <p className="text-danger">{check.data.message}</p>
        )}
        {!error && check.data?.serviceable && (
          <ul className="space-y-1.5">
            {check.data.options.map((option) => (
              <li key={option.code} className="flex justify-between gap-4">
                <span>
                  <span className="font-medium">{option.name}</span>{' '}
                  <span className="text-ink-muted">
                    · {formatShortDate(option.estimated_from)}–
                    {formatShortDate(option.estimated_to)}
                  </span>
                </span>
                <span className="tabular text-ink-muted">
                  {option.fee === '0.00' ? 'Free' : formatMoney(option.fee)}
                  {option.free_above && option.fee !== '0.00'
                    ? ` · free above ${formatMoney(option.free_above)}`
                    : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** schema.org Product data from verified API fields only (no ratings are invented). */
export function ProductJsonLd({
  product,
  variant,
  url,
}: {
  product: ProductDetail;
  variant: Variant;
  url: string;
}) {
  if (product.is_sample) return null; // never publish structured data for fictional sample products
  const data = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    description: product.description ?? undefined,
    sku: variant.sku,
    image: product.images.map((i) => (i.url.startsWith('http') ? i.url : new URL(i.url, url).href)),
    category: product.category.name,
    offers:
      variant.price.available && variant.price.amount
        ? {
            '@type': 'Offer',
            url,
            priceCurrency: 'INR',
            price: variant.price.amount,
            availability:
              variant.stock_status === 'out_of_stock'
                ? 'https://schema.org/OutOfStock'
                : 'https://schema.org/InStock',
          }
        : undefined,
  };
  // Escape '<' so product text can never close the script element if pages are pre-rendered.
  const json = JSON.stringify(data).replace(/</g, String.fromCharCode(92) + 'u003c');
  return <script type="application/ld+json">{json}</script>;
}
