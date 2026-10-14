import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';

import { ApiError } from '@/api/client';

/**
 * Copy the backend's per-field validation messages onto a react-hook-form form.
 * Returns true when at least one field error was applied.
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
): boolean {
  if (!(error instanceof ApiError)) return false;
  let applied = false;
  for (const [field, message] of Object.entries(error.fieldErrors)) {
    if ((fields as readonly string[]).includes(field)) {
      setError(field as Path<T>, { message });
      applied = true;
    }
  }
  return applied;
}

/** Message for a form-level alert (network problems get a friendlier wording). */
export function errorMessage(
  error: unknown,
  fallback = 'Something went wrong. Please try again.',
): string {
  if (error instanceof ApiError) {
    if (error.code === 'NETWORK_ERROR')
      return 'We could not reach the store. Check your connection.';
    if (error.code === 'RATE_LIMITED')
      return 'Too many attempts. Please wait a few minutes and try again.';
    return error.message;
  }
  return fallback;
}

/**
 * Only allow redirects to paths on this site after sign-in ("/account", not "//evil.example" or
 * "https://…"), preventing open-redirect attacks through the ?next= parameter.
 */
export function safeNext(next: string | null | undefined, fallback = '/account'): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) {
    return fallback;
  }
  return next;
}
