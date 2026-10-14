/**
 * Typed API client.
 *
 * - Types come from `schema.d.ts`, generated from the backend's OpenAPI contract (`npm run gen:api`).
 * - Cookies carry the session; JavaScript never sees auth tokens (ADR-0003).
 * - Unsafe requests send the CSRF token from the `csrf_token` cookie (double-submit pattern).
 * - A 401 SESSION_EXPIRED triggers one silent refresh, then the original request is retried.
 * - Failures are thrown as `ApiError` with the backend's error `code` so UI code can branch on it.
 */
import createClient from 'openapi-fetch';

import type { paths } from './schema';

// Empty VITE_API_ORIGIN = same origin. An absolute base keeps Request() valid in every runtime.
const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || window.location.origin;
const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string | null;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(status: number, body: Partial<ApiErrorBody> | undefined) {
    const error = body?.error;
    super(error?.message ?? 'Something went wrong. Please try again.');
    this.name = 'ApiError';
    this.status = status;
    this.code = error?.code ?? (status === 0 ? 'NETWORK_ERROR' : 'UNKNOWN_ERROR');
    this.details = error?.details ?? {};
    this.requestId = error?.request_id ?? null;
  }

  /** Per-field validation messages from a 422 VALIDATION_ERROR response. */
  get fieldErrors(): Record<string, string> {
    const fields = this.details.fields;
    return fields && typeof fields === 'object' ? (fields as Record<string, string>) : {};
  }
}

export function readCookie(name: string): string | null {
  const match = document.cookie
    .split('; ')
    .find((part) => part.startsWith(`${encodeURIComponent(name)}=`));
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : null;
}

let csrfPromise: Promise<string> | null = null;

/** Return the CSRF token, asking the backend to issue the cookie if the browser has none. */
export async function ensureCsrfToken(): Promise<string> {
  const existing = readCookie('csrf_token');
  if (existing) return existing;
  csrfPromise ??= fetch(`${API_ORIGIN}/api/v1/auth/csrf`, { credentials: 'include' })
    .then(async (res) => ((await res.json()) as { csrf_token: string }).csrf_token)
    .finally(() => {
      csrfPromise = null;
    });
  return csrfPromise;
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  refreshPromise ??= (async () => {
    try {
      const token = await ensureCsrfToken();
      const res = await fetch(`${API_ORIGIN}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRF-Token': token },
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function send(request: Request): Promise<Response> {
  if (UNSAFE.has(request.method)) {
    request.headers.set('X-CSRF-Token', await ensureCsrfToken());
  }
  return fetch(request);
}

/** fetch wrapper used by openapi-fetch: CSRF header + one transparent session refresh. */
export async function apiFetch(input: Request): Promise<Response> {
  const retryCopy = input.clone();
  const response = await send(input);
  if (response.status !== 401 || input.url.includes('/api/v1/auth/')) return response;

  const body = (await response
    .clone()
    .json()
    .catch(() => undefined)) as Partial<ApiErrorBody> | undefined;
  if (body?.error?.code !== 'SESSION_EXPIRED') return response;
  return (await refreshSession()) ? send(retryCopy) : response;
}

export const api = createClient<paths>({
  baseUrl: API_ORIGIN,
  credentials: 'include',
  fetch: apiFetch,
});

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/**
 * Await an openapi-fetch call and return its data, or throw `ApiError`.
 * Usage: `const product = await unwrap(api.GET('/api/v1/products/{slug}', { params }))`.
 */
export async function unwrap<T>(call: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await call;
  } catch {
    throw new ApiError(0, {
      error: {
        code: 'NETWORK_ERROR',
        message: 'We could not reach the store. Check your connection.',
      },
    });
  }
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(result.response.status, result.error as Partial<ApiErrorBody> | undefined);
  }
  return result.data as T;
}
