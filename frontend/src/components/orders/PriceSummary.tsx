import type { components } from '@/api/schema';
import { cn } from '@/lib/cn';
import { formatMoney, hasPaise } from '@/lib/format';

type PriceRow = components['schemas']['PriceRowOut'];

/**
 * The backend's price breakdown (cart, checkout and orders use the same rows). Amounts are shown
 * exactly as calculated by the server — nothing is added up here.
 */
export function PriceSummary({
  rows,
  shippingLabel,
  caption = 'Price summary',
  className,
}: {
  rows: PriceRow[];
  shippingLabel?: string | null;
  caption?: string;
  className?: string;
}) {
  const paise = rows.some((r) => hasPaise(r.amount));
  return (
    <table className={cn('w-full text-sm', className)}>
      <caption className="sr-only">{caption}</caption>
      <tbody>
        {rows.map((row) => {
          const negative = row.amount.startsWith('-');
          return (
            <tr
              key={row.key}
              className={cn(row.key === 'total' && 'border-t border-line text-base font-medium')}
            >
              <th scope="row" className="py-1.5 text-left font-normal">
                {row.key === 'total'
                  ? 'Total (incl. GST)'
                  : row.key === 'shipping'
                    ? `Shipping (${shippingLabel ?? 'estimated'})`
                    : row.label}
              </th>
              <td className={cn('tabular py-1.5 text-right', negative && 'text-success')}>
                {row.key === 'shipping' && row.amount === '0.00'
                  ? 'Free'
                  : negative
                    ? `− ${formatMoney(row.amount.slice(1), { paise })}`
                    : formatMoney(row.amount, { paise })}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
