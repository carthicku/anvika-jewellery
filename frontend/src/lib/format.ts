/**
 * Display formatting only — never arithmetic. Money arrives from the API as strings ("27402.74").
 */

const inrWhole = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});
const inrPaise = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function hasPaise(value: string | null | undefined): boolean {
  return Boolean(value?.includes('.') && !/\.0+$/.test(value));
}

/**
 * "27402.74" → "₹27,402.74"; "13287.00" → "₹13,287". Pass `paise: true` to always show two
 * decimals (used when several amounts are shown together, so they line up consistently).
 */
export function formatMoney(
  value: string | null | undefined,
  options: { paise?: boolean } = {},
): string {
  if (value === null || value === undefined || value === '') return '';
  const asNumber = Number(value); // display only: amounts are well within float precision
  if (!Number.isFinite(asNumber)) return '';
  return (options.paise || hasPaise(value) ? inrPaise : inrWhole).format(asNumber);
}

/** "3.480" → "3.48 g" */
export function formatWeight(value: string | null | undefined, unit = 'g'): string {
  if (!value) return '';
  const trimmed = value.replace(/\.?0+$/, '');
  return `${trimmed} ${unit}`;
}

const dateFormat = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' });
const dateTimeFormat = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

export function formatShortDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

export const METAL_COLOUR_LABELS: Record<string, string> = {
  yellow: 'Yellow gold',
  white: 'White gold',
  rose: 'Rose gold',
  two_tone: 'Two-tone gold',
};
