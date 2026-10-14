import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2, MailCheck } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';
import { useForm } from 'react-hook-form';

import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import type { z } from 'zod';

import { ApiError } from '@/api/client';
import {
  useForgotPassword,
  useLogin,
  useMe,
  useRegister,
  useResetPassword,
  useVerifyEmail,
} from '@/api/queries/account';
import { useMergeGuestWishlist } from '@/api/queries/wishlist';
import { PageMeta } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Alert, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input } from '@/components/ui/Field';
import { Spinner } from '@/components/ui/Spinner';
import { applyServerErrors, errorMessage, safeNext } from '@/lib/forms';
import { loginSchema, registerSchema, resetSchema } from '@/lib/validation/account';

function AuthLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-md px-4 py-14 sm:py-20">
      <h1 className="text-center font-display text-4xl font-medium tracking-tight">{title}</h1>
      {description && <p className="mt-3 text-center text-ink-muted">{description}</p>}
      <div className="mt-10 rounded-md border border-line bg-surface p-6 sm:p-8">{children}</div>
      {footer && <div className="mt-6 text-center text-sm text-ink-muted">{footer}</div>}
    </div>
  );
}

const linkCls =
  'font-medium text-ink underline decoration-gold underline-offset-4 hover:decoration-ink';

/** Redirect signed-in visitors away from sign-in/registration pages. */
function useRedirectIfSignedIn() {
  const me = useMe();
  const [params] = useSearchParams();
  return { me, target: safeNext(params.get('next')) };
}

export function LoginPage() {
  const { me, target } = useRedirectIfSignedIn();
  const [params] = useSearchParams();
  const login = useLogin();
  const merge = useMergeGuestWishlist();
  const navigate = useNavigate();
  const form = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });
  const { errors } = form.formState;

  if (me.data) return <Navigate to={target} replace />;

  const onSubmit = form.handleSubmit((values) => {
    login.mutate(values, {
      onSuccess: () => {
        // Move the guest wishlist into the account, then continue where the shopper was going.
        void merge().then(() => navigate(target, { replace: true }));
      },
    });
  });

  return (
    <>
      <PageMeta title="Sign in" path="/login" noindex />
      <AuthLayout
        title="Welcome back"
        description="Sign in to see your orders, addresses and saved pieces."
        footer={
          <>
            New here?{' '}
            <Link
              to={`/register${params.toString() ? `?${params.toString()}` : ''}`}
              className={linkCls}
            >
              Create an account
            </Link>
          </>
        }
      >
        <form onSubmit={onSubmit} noValidate className="space-y-5">
          {login.isError && <Alert tone="danger" title={errorMessage(login.error)} />}
          <FormField label="Email" error={errors.email?.message}>
            <Input type="email" autoComplete="email" {...form.register('email')} />
          </FormField>
          <FormField label="Password" error={errors.password?.message}>
            <Input type="password" autoComplete="current-password" {...form.register('password')} />
          </FormField>
          <div className="flex justify-end">
            <Link
              to="/forgot-password"
              className="text-sm text-ink-muted underline underline-offset-4 hover:text-ink"
            >
              Forgot your password?
            </Link>
          </div>
          <Button type="submit" size="lg" className="w-full" loading={login.isPending}>
            Sign in
          </Button>
        </form>
      </AuthLayout>
    </>
  );
}

export function RegisterPage() {
  const { me, target } = useRedirectIfSignedIn();
  const [params] = useSearchParams();
  const registerUser = useRegister();
  const merge = useMergeGuestWishlist();
  const navigate = useNavigate();
  const form = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: '', email: '', phone: '', password: '' },
  });
  const { errors } = form.formState;

  if (me.data) return <Navigate to={target} replace />;

  const onSubmit = form.handleSubmit((values) => {
    registerUser.mutate(
      { ...values, phone: values.phone || null },
      {
        onSuccess: () => {
          void merge().then(() => navigate(target, { replace: true }));
        },
        onError: (error) => {
          applyServerErrors(error, form.setError, ['full_name', 'email', 'phone', 'password']);
        },
      },
    );
  });

  return (
    <>
      <PageMeta title="Create an account" path="/register" noindex />
      <AuthLayout
        title="Create your account"
        description="Track orders, save addresses and keep a wishlist across devices."
        footer={
          <>
            Already have an account?{' '}
            <Link
              to={`/login${params.toString() ? `?${params.toString()}` : ''}`}
              className={linkCls}
            >
              Sign in
            </Link>
          </>
        }
      >
        <form onSubmit={onSubmit} noValidate className="space-y-5">
          {registerUser.isError && (
            <Alert tone="danger" title={errorMessage(registerUser.error)}>
              {registerUser.error instanceof ApiError &&
                registerUser.error.code === 'EMAIL_IN_USE' && (
                  <Link to="/forgot-password" className={linkCls}>
                    Reset your password
                  </Link>
                )}
            </Alert>
          )}
          <FormField label="Full name" required error={errors.full_name?.message}>
            <Input autoComplete="name" {...form.register('full_name')} />
          </FormField>
          <FormField label="Email" required error={errors.email?.message}>
            <Input type="email" autoComplete="email" {...form.register('email')} />
          </FormField>
          <FormField
            label="Mobile number"
            hint="Optional — for delivery updates"
            error={errors.phone?.message}
          >
            <Input type="tel" autoComplete="tel" inputMode="tel" {...form.register('phone')} />
          </FormField>
          <FormField
            label="Password"
            required
            hint="At least 10 characters. A short phrase works well."
            error={errors.password?.message}
          >
            <Input type="password" autoComplete="new-password" {...form.register('password')} />
          </FormField>
          <Button type="submit" size="lg" className="w-full" loading={registerUser.isPending}>
            Create account
          </Button>
          <p className="text-xs leading-relaxed text-ink-muted">
            By creating an account you agree to our{' '}
            <Link to="/terms-and-conditions" className="underline underline-offset-2">
              terms
            </Link>{' '}
            and{' '}
            <Link to="/privacy-policy" className="underline underline-offset-2">
              privacy policy
            </Link>
            .
          </p>
        </form>
      </AuthLayout>
    </>
  );
}

export function ForgotPasswordPage() {
  const forgot = useForgotPassword();
  const form = useForm<{ email: string }>({
    resolver: zodResolver(loginSchema.pick({ email: true })),
    defaultValues: { email: '' },
  });

  return (
    <>
      <PageMeta title="Reset your password" path="/forgot-password" noindex />
      <AuthLayout
        title="Reset your password"
        description="Enter your email and we’ll send you a link to choose a new password."
        footer={
          <Link to="/login" className={linkCls}>
            Back to sign in
          </Link>
        }
      >
        {forgot.isSuccess ? (
          <div role="status" className="text-center">
            <MailCheck className="mx-auto size-8 text-gold" strokeWidth={1.25} aria-hidden="true" />
            <p className="mt-4">{forgot.data.message}</p>
            <p className="mt-2 text-sm text-ink-muted">The link is valid for 30 minutes.</p>
          </div>
        ) : (
          <form
            noValidate
            className="space-y-5"
            onSubmit={form.handleSubmit((values) => {
              forgot.mutate(values.email);
            })}
          >
            {forgot.isError && <Alert tone="danger" title={errorMessage(forgot.error)} />}
            <FormField label="Email" error={form.formState.errors.email?.message}>
              <Input type="email" autoComplete="email" {...form.register('email')} />
            </FormField>
            <Button type="submit" size="lg" className="w-full" loading={forgot.isPending}>
              Send reset link
            </Button>
          </form>
        )}
      </AuthLayout>
    </>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const reset = useResetPassword();
  const form = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: '', confirm: '' },
  });
  const { errors } = form.formState;

  return (
    <>
      <PageMeta title="Choose a new password" path="/reset-password" noindex />
      <AuthLayout title="Choose a new password">
        {!token ? (
          <Alert tone="danger" title="This reset link is incomplete.">
            Please use the link from your email, or{' '}
            <Link to="/forgot-password" className={linkCls}>
              request a new one
            </Link>
            .
          </Alert>
        ) : reset.isSuccess ? (
          <div role="status" className="text-center">
            <CheckCircle2
              className="mx-auto size-8 text-success"
              strokeWidth={1.25}
              aria-hidden="true"
            />
            <p className="mt-4">
              Your password has been changed and other devices were signed out.
            </p>
            <Button asChild className="mt-6">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        ) : (
          <form
            noValidate
            className="space-y-5"
            onSubmit={form.handleSubmit((values) => {
              reset.mutate(
                { token, password: values.password },
                {
                  onError: (error) => {
                    applyServerErrors(error, form.setError, ['password']);
                  },
                },
              );
            })}
          >
            {reset.isError && (
              <Alert tone="danger" title={errorMessage(reset.error)}>
                <Link to="/forgot-password" className={linkCls}>
                  Request a new link
                </Link>
              </Alert>
            )}
            <FormField
              label="New password"
              hint="At least 10 characters."
              error={errors.password?.message}
            >
              <Input type="password" autoComplete="new-password" {...form.register('password')} />
            </FormField>
            <FormField label="Repeat new password" error={errors.confirm?.message}>
              <Input type="password" autoComplete="new-password" {...form.register('confirm')} />
            </FormField>
            <Button type="submit" size="lg" className="w-full" loading={reset.isPending}>
              Change password
            </Button>
          </form>
        )}
      </AuthLayout>
    </>
  );
}

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const verify = useVerifyEmail();
  const started = useRef(false);
  const { mutate } = verify;

  useEffect(() => {
    // Run once, even under StrictMode's double effects (tokens are single-use).
    if (!token || started.current) return;
    started.current = true;
    mutate(token);
  }, [token, mutate]);

  return (
    <>
      <PageMeta title="Confirm your email" path="/verify-email" noindex />
      <AuthLayout title="Confirm your email">
        <div className="text-center" aria-live="polite">
          {!token && <Alert tone="danger" title="This confirmation link is incomplete." />}
          {token && (verify.isPending || verify.isIdle) && (
            <div className="flex flex-col items-center gap-3">
              <Spinner label="Confirming your email" />
              <Skeleton className="h-4 w-40" />
            </div>
          )}
          {verify.isSuccess && (
            <>
              <CheckCircle2
                className="mx-auto size-8 text-success"
                strokeWidth={1.25}
                aria-hidden="true"
              />
              <p className="mt-4">{verify.data.message}</p>
              <Button asChild className="mt-6">
                <Link to="/account">Go to your account</Link>
              </Button>
            </>
          )}
          {verify.isError && (
            <Alert tone="danger" title={errorMessage(verify.error)}>
              You can request a new link from{' '}
              <Link to="/account" className={linkCls}>
                your account
              </Link>
              .
            </Alert>
          )}
        </div>
      </AuthLayout>
    </>
  );
}
