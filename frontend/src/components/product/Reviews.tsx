/**
 * Customer reviews on the product page. Only reviews approved by staff are shown, and only
 * customers whose order with this piece was delivered can write one (checked by the backend).
 * Nothing here is invented: with no approved reviews the section says so.
 */
import { Star } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';

import { ApiError } from '@/api/client';
import { useMe } from '@/api/queries/account';
import {
  useMyReview,
  useProductReviews,
  useSaveReview,
  type MyReviewState,
} from '@/api/queries/reviews';
import { Button } from '@/components/ui/Button';
import { Alert, Badge, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { cn } from '@/lib/cn';
import { formatShortDate } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

export function Stars({ rating, className }: { rating: number; className?: string }) {
  return (
    <span
      role="img"
      aria-label={`${String(rating)} out of 5 stars`}
      className={cn('inline-flex gap-0.5 text-gold-deep', className)}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          aria-hidden="true"
          className={cn('size-4', n <= Math.round(rating) ? 'fill-current' : 'opacity-40')}
        />
      ))}
    </span>
  );
}

function ReviewForm({ slug, state }: { slug: string; state: MyReviewState }) {
  const existing = state.review;
  const [rating, setRating] = useState(existing?.rating ?? 0);
  const [title, setTitle] = useState(existing?.title ?? '');
  const [body, setBody] = useState(existing?.body ?? '');
  const save = useSaveReview(slug);
  const { notify } = useToast();
  const errors: Record<string, string> =
    save.error instanceof ApiError ? save.error.fieldErrors : {};
  return (
    <form
      className="space-y-4 rounded-md border border-line bg-surface p-5"
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate(
          { rating, title: title.trim(), body: body.trim() },
          {
            onSuccess: () => {
              notify('Thank you. Your review will appear once it has been approved.', 'success');
            },
          },
        );
      }}
    >
      <h3 className="font-medium">{existing ? 'Edit your review' : 'Write a review'}</h3>
      {save.isError && !Object.keys(errors).length && (
        <Alert tone="danger" title={errorMessage(save.error)} />
      )}
      <fieldset>
        <legend className="text-sm font-medium">
          Your rating<span aria-hidden="true">*</span>
        </legend>
        <div className="mt-2 flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <label key={n} className="cursor-pointer">
              <input
                type="radio"
                name="rating"
                value={n}
                className="peer sr-only"
                checked={rating === n}
                required
                onChange={() => {
                  setRating(n);
                }}
              />
              <span className="sr-only">
                {n} {n === 1 ? 'star' : 'stars'}
              </span>
              <Star
                aria-hidden="true"
                className={cn(
                  'size-7 rounded-sm text-gold-deep peer-focus-visible:outline-2 peer-focus-visible:outline-focus',
                  n <= rating ? 'fill-current' : 'opacity-40',
                )}
              />
            </label>
          ))}
        </div>
        {errors.rating && <p className="mt-1 text-sm text-danger">{errors.rating}</p>}
      </fieldset>
      <FormField label="Title" required error={errors.title}>
        <Input
          value={title}
          minLength={3}
          maxLength={120}
          required
          onChange={(e) => {
            setTitle(e.target.value);
          }}
        />
      </FormField>
      <FormField label="Your review" required hint="At least 20 characters." error={errors.body}>
        <Textarea
          rows={4}
          minLength={20}
          maxLength={2000}
          required
          value={body}
          onChange={(e) => {
            setBody(e.target.value);
          }}
        />
      </FormField>
      <p className="text-xs text-ink-muted">
        Shown with your first name and initial. Reviews are checked by our team before they appear.
      </p>
      <Button type="submit" loading={save.isPending} disabled={rating === 0}>
        {existing ? 'Update review' : 'Submit review'}
      </Button>
    </form>
  );
}

function WriteReview({ slug }: { slug: string }) {
  const me = useMe();
  const signedIn = Boolean(me.data);
  const mine = useMyReview(slug, signedIn);
  if (me.isPending) return null;
  if (!signedIn) {
    return (
      <p className="text-sm text-ink-muted">
        Bought this piece?{' '}
        <Link
          to={`/login?next=${encodeURIComponent(`/products/${slug}`)}`}
          className="underline underline-offset-4"
        >
          Sign in
        </Link>{' '}
        to review it after delivery.
      </p>
    );
  }
  if (mine.isPending) return <Skeleton className="h-24" />;
  if (mine.isError) return null;
  const state = mine.data;
  return (
    <div className="space-y-3">
      {state.review && (
        <p className="flex flex-wrap items-center gap-2 text-sm">
          Your review: <Badge tone="neutral">{state.review.status_label}</Badge>
        </p>
      )}
      {state.can_review ? (
        <ReviewForm key={state.review?.updated_at ?? 'new'} slug={slug} state={state} />
      ) : (
        <p className="text-sm text-ink-muted">
          You can review this piece once an order containing it has been delivered.
        </p>
      )}
    </div>
  );
}

export function ProductReviewsSection({ slug }: { slug: string }) {
  const [page, setPage] = useState(1);
  const reviews = useProductReviews(slug, page);
  const summary = reviews.data?.summary;
  const list = reviews.data?.reviews;
  return (
    <section aria-labelledby="reviews-heading" className="mt-20 border-t border-line pt-16">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 id="reviews-heading" className="font-display text-3xl">
          Reviews
        </h2>
        {summary && summary.count > 0 && summary.average && (
          <p className="flex items-center gap-2 text-sm">
            <Stars rating={Number(summary.average)} />
            <span>
              {summary.average} out of 5 · {summary.count}{' '}
              {summary.count === 1 ? 'review' : 'reviews'}
            </span>
          </p>
        )}
      </div>
      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_22rem]">
        <div className="min-w-0">
          {reviews.isPending ? (
            <Skeleton className="h-32" />
          ) : !list || list.items.length === 0 ? (
            <p className="text-sm text-ink-muted">No reviews yet.</p>
          ) : (
            <>
              <ul className="divide-y divide-line border-y border-line">
                {list.items.map((r) => (
                  <li key={r.id} className="py-5">
                    <Stars rating={r.rating} />
                    <p className="mt-2 font-medium">{r.title}</p>
                    <p className="mt-1 text-sm whitespace-pre-line">{r.body}</p>
                    <p className="mt-2 text-xs text-ink-muted">
                      {r.author_name}
                      {r.verified_purchase && ' · Verified purchase'} ·{' '}
                      <time dateTime={r.created_at}>{formatShortDate(r.created_at)}</time>
                    </p>
                  </li>
                ))}
              </ul>
              {list.pages > 1 && (
                <div className="mt-4 flex items-center gap-3 text-sm">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => {
                      setPage(page - 1);
                    }}
                  >
                    Newer
                  </Button>
                  <span>
                    Page {page} of {list.pages}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={page >= list.pages}
                    onClick={() => {
                      setPage(page + 1);
                    }}
                  >
                    Older
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
        <WriteReview slug={slug} />
      </div>
    </section>
  );
}
