/**
 * Small building blocks shared by admin pages (docs/design/COMPONENT_LIBRARY.md → Admin).
 * Presentational only: pages fetch data and pass it in.
 */
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router';

import { PageMeta } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { DialogClose, DialogContent, DialogRoot } from '@/components/ui/Dialog';
import { Alert, Skeleton } from '@/components/ui/Feedback';
import { cn } from '@/lib/cn';
import { errorMessage } from '@/lib/forms';

export function AdminPage({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-7xl">
      <PageMeta title={`${title} · Admin`} path="/admin" noindex />
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="font-display text-3xl sm:text-4xl">{title}</h1>
          {description && <p className="mt-1 max-w-2xl text-sm text-ink-muted">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function Panel({
  title,
  actions,
  children,
  className,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('min-w-0 rounded-md border border-line bg-surface p-5', className)}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-base font-medium">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-line bg-surface p-5">
      <p className="text-xs tracking-(--tracking-eyebrow) text-ink-muted uppercase">{label}</p>
      <p className="mt-2 font-display text-3xl lining-nums tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

/** Accessible table with loading, empty and error states; scrolls sideways inside its box only. */
export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  loading,
  error,
  empty = 'Nothing here yet.',
}: {
  caption: string;
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: unknown;
  empty?: string;
}) {
  if (error) return <Alert tone="danger" title={errorMessage(error)} />;
  if (loading && !rows) return <Skeleton className="h-48" />;
  if (!rows || rows.length === 0) return <p className="py-6 text-sm text-ink-muted">{empty}</p>;
  return (
    <div
      role="region"
      aria-label={caption}
      // A scrollable table must be reachable by keyboard (WCAG 2.1.1, axe scrollable-region-focusable).
      // eslint-disable-next-line jsx-a11y-x/no-noninteractive-tabindex
      tabIndex={0}
      className="overflow-x-auto rounded-md border border-line bg-surface focus-visible:outline-2 focus-visible:outline-focus"
    >
      <table className="w-full min-w-[32rem] text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-line bg-surface-muted/60 text-xs text-ink-muted uppercase">
          <tr>
            {columns.map((c) => (
              <th key={c.header} scope="col" className={cn('px-3 py-2 font-medium', c.className)}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="align-top">
              {columns.map((c) => (
                <td key={c.header} className={cn('px-3 py-2.5', c.className)}>
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Page number kept in the URL (?page=), so lists can be shared and survive reloads. */
export function usePageParam(): [number, (page: number) => void] {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  return [
    page,
    (next) => {
      const copy = new URLSearchParams(params);
      if (next <= 1) copy.delete('page');
      else copy.set('page', String(next));
      setParams(copy);
    },
  ];
}

export function Pager({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (pages <= 1) return <p className="mt-3 text-xs text-ink-muted">{total} total</p>;
  return (
    <nav aria-label="Pages" className="mt-3 flex items-center gap-3 text-sm">
      <Button
        variant="ghost"
        size="sm"
        disabled={page <= 1}
        onClick={() => {
          onChange(page - 1);
        }}
        aria-label="Previous page"
      >
        <ChevronLeft className="size-4" aria-hidden="true" />
      </Button>
      <span>
        Page {page} of {pages} · {total} total
      </span>
      <Button
        variant="ghost"
        size="sm"
        disabled={page >= pages}
        onClick={() => {
          onChange(page + 1);
        }}
        aria-label="Next page"
      >
        <ChevronRight className="size-4" aria-hidden="true" />
      </Button>
    </nav>
  );
}

/**
 * A button that opens a dialog with a form. `onSubmit` returns a promise; the dialog closes when
 * it resolves and shows the server's message when it rejects.
 */
export function FormDialog({
  trigger,
  title,
  description,
  submitLabel,
  danger,
  onSubmit,
  children,
}: {
  trigger: (open: () => void) => ReactNode;
  title: string;
  description?: ReactNode;
  submitLabel: string;
  danger?: boolean;
  onSubmit: (form: FormData) => Promise<unknown>;
  children?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return (
    <DialogRoot
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) setError(null);
      }}
    >
      {trigger(() => {
        setOpen(true);
      })}
      <DialogContent title={title} description={description}>
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            setBusy(true);
            setError(null);
            onSubmit(new FormData(event.currentTarget))
              .then(() => {
                setOpen(false);
              })
              .catch((err: unknown) => {
                setError(err);
              })
              .finally(() => {
                setBusy(false);
              });
          }}
        >
          {error ? <Alert tone="danger" title={errorMessage(error)} /> : null}
          {children}
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <DialogClose asChild>
              <Button variant="ghost" type="button">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" variant={danger ? 'danger' : 'primary'} loading={busy}>
              {submitLabel}
            </Button>
          </div>
        </form>
      </DialogContent>
    </DialogRoot>
  );
}

export function field(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === 'string' ? value.trim() : '';
}

export function Json({ value }: { value: unknown }) {
  return (
    <pre className="max-h-48 overflow-auto rounded-sm bg-surface-muted p-2 text-xs whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
