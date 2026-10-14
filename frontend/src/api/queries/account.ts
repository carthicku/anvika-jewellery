import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';

import type { components } from '../schema';
import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';

export type User = components['schemas']['UserOut'];
export type Address = components['schemas']['AddressOut'];
export type AddressInput = components['schemas']['AddressIn'];
export type AccountSession = components['schemas']['SessionOut'];

/** The signed-in user (null for guests). Cached; refreshed after sign-in/out. */
export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: async () => (await unwrap(api.GET('/api/v1/auth/me'))).user ?? null,
    staleTime: 60_000,
  });
}

function useAfterAuthChange() {
  const client = useQueryClient();
  return (user: User | null) => {
    client.setQueryData(queryKeys.me, user);
    // Anything personalised must be refetched for the new identity.
    void client.invalidateQueries({ queryKey: queryKeys.wishlist });
    void client.invalidateQueries({ queryKey: queryKeys.cart });
    void client.invalidateQueries({ queryKey: ['account'] });
  };
}

export function useLogin() {
  const after = useAfterAuthChange();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      unwrap(api.POST('/api/v1/auth/login', { body })),
    onSuccess: (data) => {
      after(data.user ?? null);
    },
  });
}

export function useRegister() {
  const after = useAfterAuthChange();
  return useMutation({
    mutationFn: (body: {
      full_name: string;
      email: string;
      password: string;
      phone: string | null;
    }) => unwrap(api.POST('/api/v1/auth/register', { body })),
    onSuccess: (data) => {
      after(data.user ?? null);
    },
  });
}

/**
 * Sign out, leave the page, THEN forget the user. Clearing first would let the account-page guard
 * redirect to sign-in before the intended destination is reached.
 */
export function useLogout() {
  const client = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: ({ all = false }: { all?: boolean; redirectTo: string }) =>
      unwrap(api.POST(all ? '/api/v1/auth/logout-all' : '/api/v1/auth/logout')),
    onSettled: async (_data, _error, { redirectTo }) => {
      await navigate(redirectTo, { replace: true });
      client.setQueryData(queryKeys.me, null);
      client.removeQueries({ queryKey: ['account'] });
      client.removeQueries({ queryKey: queryKeys.wishlist });
      void client.invalidateQueries({ queryKey: queryKeys.cart });
    },
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) =>
      unwrap(api.POST('/api/v1/auth/forgot-password', { body: { email } })),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (body: { token: string; password: string }) =>
      unwrap(api.POST('/api/v1/auth/reset-password', { body })),
  });
}

export function useVerifyEmail() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (token: string) =>
      unwrap(api.POST('/api/v1/auth/verify-email', { body: { token } })),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.me }),
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/v1/auth/resend-verification')),
  });
}

export function useChangePassword() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      unwrap(api.POST('/api/v1/auth/change-password', { body })),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.sessions }),
  });
}

export function useSessions() {
  return useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => unwrap(api.GET('/api/v1/auth/sessions')),
  });
}

export function useRevokeSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/v1/auth/sessions/{session_id}', { params: { path: { session_id: id } } }),
      ),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.sessions }),
  });
}

export function useUpdateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { full_name: string; phone: string | null }) =>
      unwrap(api.PATCH('/api/v1/me/profile', { body })),
    onSuccess: (user) => {
      client.setQueryData(queryKeys.me, user);
    },
  });
}

export function useAddresses(enabled = true) {
  return useQuery({
    queryKey: queryKeys.addresses,
    queryFn: () => unwrap(api.GET('/api/v1/me/addresses')),
    enabled,
  });
}

export function useSaveAddress() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: AddressInput }) =>
      id
        ? unwrap(
            api.PUT('/api/v1/me/addresses/{address_id}', {
              params: { path: { address_id: id } },
              body,
            }),
          )
        : unwrap(api.POST('/api/v1/me/addresses', { body })),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.addresses }),
  });
}

export function useDeleteAddress() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/v1/me/addresses/{address_id}', { params: { path: { address_id: id } } }),
      ),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.addresses }),
  });
}
