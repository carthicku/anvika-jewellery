import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Link, useLocation } from 'react-router';

import { cn } from '@/lib/cn';

function pageHref(search: string, pathname: string, page: number): string {
  const params = new URLSearchParams(search);
  if (page <= 1) params.delete('page');
  else params.set('page', String(page));
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

/** Real links (shareable, crawlable). Shows first, last and a window around the current page. */
export function Pagination({ page, pages }: { page: number; pages: number }) {
  const { pathname, search } = useLocation();
  if (pages <= 1) return null;

  const window = new Set([1, pages, page - 1, page, page + 1].filter((p) => p >= 1 && p <= pages));
  const numbers = [...window].sort((a, b) => a - b);
  const linkCls =
    'inline-flex size-11 items-center justify-center rounded-sm text-sm tabular hover:bg-surface-muted';

  return (
    <nav aria-label="Pagination" className="mt-12 flex items-center justify-center gap-1">
      {page > 1 ? (
        <Link
          to={pageHref(search, pathname, page - 1)}
          className={linkCls}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
        </Link>
      ) : (
        <span className={cn(linkCls, 'text-ink-subtle opacity-50')} aria-hidden="true">
          <ChevronLeft className="size-4" />
        </span>
      )}
      {numbers.map((n, i) => (
        <span key={n} className="flex items-center">
          {i > 0 && n - (numbers[i - 1] ?? n) > 1 && (
            <span className="px-1 text-ink-subtle" aria-hidden="true">
              …
            </span>
          )}
          <Link
            to={pageHref(search, pathname, n)}
            aria-current={n === page ? 'page' : undefined}
            aria-label={`Page ${n}`}
            className={cn(linkCls, n === page && 'bg-ink text-ivory hover:bg-ink')}
          >
            {n}
          </Link>
        </span>
      ))}
      {page < pages ? (
        <Link to={pageHref(search, pathname, page + 1)} className={linkCls} aria-label="Next page">
          <ChevronRight className="size-4" aria-hidden="true" />
        </Link>
      ) : (
        <span className={cn(linkCls, 'text-ink-subtle opacity-50')} aria-hidden="true">
          <ChevronRight className="size-4" />
        </span>
      )}
    </nav>
  );
}
