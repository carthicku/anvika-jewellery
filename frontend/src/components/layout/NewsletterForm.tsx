import { useId, useState, type SyntheticEvent } from 'react';

import { ApiError } from '@/api/client';
import { useNewsletterSignup } from '@/api/queries/catalogue';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { secondsSince } from '@/lib/formTiming';

// Deliberately dependency-free: this form is on every page, so it must not pull form/validation
// libraries into the initial bundle. The backend validates again.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Newsletter sign-up with explicit consent and a hidden honeypot field for bots. */
export function NewsletterForm({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  const id = useId();
  const [openedAt] = useState(() => Date.now());
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState('');
  const [errors, setErrors] = useState<{ email?: string; consent?: string }>({});
  const signup = useNewsletterSignup();

  const onSubmit = (event: SyntheticEvent) => {
    event.preventDefault();
    const next: typeof errors = {};
    if (!EMAIL_RE.test(email.trim())) next.email = 'Enter a valid email address.';
    if (!consent) next.consent = 'Please confirm you would like our emails.';
    setErrors(next);
    if (next.email) {
      document.getElementById(`${id}-email`)?.focus();
      return;
    }
    if (next.consent) {
      document.getElementById(`${id}-consent`)?.focus();
      return;
    }
    signup.mutate({
      email: email.trim(),
      consent: true,
      website,
      elapsed_seconds: secondsSince(openedAt),
      source: 'footer',
    });
  };

  const dark = tone === 'dark';
  const errorText = dark ? 'text-danger-on-dark' : 'text-danger';

  if (signup.isSuccess) {
    return (
      <p role="status" className={cn('text-sm', dark ? 'text-noir-ink' : 'text-ink')}>
        Thank you for subscribing. We write occasionally — new collections and care notes, never
        spam.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-3">
      <div className="flex gap-2">
        <label htmlFor={`${id}-email`} className="sr-only">
          Email address
        </label>
        <input
          id={`${id}-email`}
          type="email"
          autoComplete="email"
          placeholder="Your email address"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
          }}
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={errors.email ? `${id}-email-error` : undefined}
          className={cn(
            'min-h-11 min-w-0 flex-1 rounded-sm border px-3.5 text-sm',
            dark
              ? 'border-noir-muted/60 bg-transparent text-noir-ink placeholder:text-noir-muted focus-visible:border-noir-ink'
              : 'border-line-strong bg-surface',
          )}
        />
        <Button
          type="submit"
          loading={signup.isPending}
          className={dark ? 'bg-noir-ink text-noir hover:bg-noir-ink/90' : undefined}
        >
          Subscribe
        </Button>
      </div>
      {errors.email && (
        <p id={`${id}-email-error`} className={cn('text-sm', errorText)}>
          {errors.email}
        </p>
      )}
      {/* Honeypot: hidden from people and assistive tech; bots tend to fill it. */}
      <div aria-hidden="true" className="hidden">
        <label htmlFor={`${id}-website`}>Website</label>
        <input
          id={`${id}-website`}
          tabIndex={-1}
          autoComplete="off"
          value={website}
          onChange={(e) => {
            setWebsite(e.target.value);
          }}
        />
      </div>
      <label
        htmlFor={`${id}-consent`}
        className={cn(
          'flex items-start gap-2.5 text-xs leading-relaxed',
          dark ? 'text-noir-muted' : 'text-ink-muted',
        )}
      >
        <input
          id={`${id}-consent`}
          type="checkbox"
          checked={consent}
          onChange={(e) => {
            setConsent(e.target.checked);
          }}
          className="mt-0.5 size-4 shrink-0 accent-gold"
          aria-invalid={errors.consent ? true : undefined}
          aria-describedby={errors.consent ? `${id}-consent-error` : undefined}
        />
        I would like to receive emails about new collections and offers. I can unsubscribe at any
        time.
      </label>
      {errors.consent && (
        <p id={`${id}-consent-error`} className={cn('text-sm', errorText)}>
          {errors.consent}
        </p>
      )}
      {signup.isError && (
        <p role="alert" className={cn('text-sm', errorText)}>
          {signup.error instanceof ApiError && signup.error.code === 'RATE_LIMITED'
            ? 'Too many attempts. Please try again later.'
            : 'We couldn’t subscribe you just now. Please try again.'}
        </p>
      )}
    </form>
  );
}
