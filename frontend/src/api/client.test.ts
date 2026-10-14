import { describe, expect, it } from 'vitest';

import { api, ApiError, unwrap } from '@/api/client';
import { mockFetch } from '@/test/utils';

describe('api client', () => {
  it('returns data on success', async () => {
    mockFetch({ 'GET /api/v1/health': { body: { status: 'ok' } } });
    await expect(unwrap(api.GET('/api/v1/health'))).resolves.toEqual({ status: 'ok' });
  });

  it('throws ApiError with the backend error code and field errors', async () => {
    mockFetch({
      'GET /api/v1/health': {
        status: 422,
        body: {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Please check the highlighted fields.',
            details: { fields: { deep: 'Input should be a valid boolean' } },
            request_id: 'abc12345',
          },
        },
      },
    });
    const error = await unwrap(api.GET('/api/v1/health')).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.code).toBe('VALIDATION_ERROR');
    expect(apiError.fieldErrors).toEqual({ deep: 'Input should be a valid boolean' });
    expect(apiError.requestId).toBe('abc12345');
  });

  it('maps network failures to NETWORK_ERROR', async () => {
    mockFetch({});
    const error = (await unwrap(api.GET('/api/v1/health')).catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe('NETWORK_ERROR');
  });

  it('sends the CSRF token on unsafe requests, fetching it first when missing', async () => {
    const fetchMock = mockFetch({
      'GET /api/v1/auth/csrf': () => {
        document.cookie = 'csrf_token=tok123; path=/';
        return { body: { csrf_token: 'tok123' } };
      },
      'POST /api/v1/health': {
        status: 405,
        body: { error: { code: 'METHOD_NOT_ALLOWED', message: 'x' } },
      },
    });
    // POST /health does not exist in the typed schema; call the raw fetch wrapper path instead.
    await (api as unknown as { POST: (p: string) => Promise<unknown> }).POST('/api/v1/health');
    const post = fetchMock.mock.calls
      .map(([input]) => input as Request)
      .find((request) => request.method === 'POST');
    expect(post?.headers.get('X-CSRF-Token')).toBe('tok123');
  });

  it('refreshes an expired session once and retries the request', async () => {
    document.cookie = 'csrf_token=tok; path=/';
    let calls = 0;
    const fetchMock = mockFetch({
      'GET /api/v1/health': () => {
        calls += 1;
        return calls === 1
          ? { status: 401, body: { error: { code: 'SESSION_EXPIRED', message: 'expired' } } }
          : { body: { status: 'ok' } };
      },
      'POST /api/v1/auth/refresh': { body: { ok: true } },
    });
    await expect(unwrap(api.GET('/api/v1/health'))).resolves.toEqual({ status: 'ok' });
    expect(calls).toBe(2);
    const urls = fetchMock.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(urls.some((url) => url.endsWith('/api/v1/auth/refresh'))).toBe(true);
  });
});
