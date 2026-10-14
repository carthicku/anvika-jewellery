import { Search, X } from 'lucide-react';
import { useDeferredValue, useId, useState, type SyntheticEvent } from 'react';
import { Link, useNavigate } from 'react-router';

import { useSuggestions } from '@/api/queries/catalogue';
import { DialogContent, DialogRoot } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { formatMoney } from '@/lib/format';

/** Search with live suggestions. Enter (or "See all results") goes to /search?q=… */
export function SearchDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [query, setQuery] = useState('');
  const deferred = useDeferredValue(query.trim());
  const suggestions = useSuggestions(deferred);
  const navigate = useNavigate();
  const listId = useId();

  const close = () => {
    onOpenChange(false);
  };

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    close();
    void navigate(`/search?q=${encodeURIComponent(q)}`);
  };

  const data = suggestions.data;
  const hasResults = Boolean(data && (data.products.length || data.categories.length));

  return (
    <DialogRoot open={open} onOpenChange={onOpenChange}>
      <DialogContent
        title="Search the store"
        hideTitle
        className="top-[12vh] max-w-2xl translate-y-0"
      >
        <form role="search" onSubmit={submit} className="relative">
          <label htmlFor={`${listId}-input`} className="sr-only">
            Search jewellery
          </label>
          <Search
            className="pointer-events-none absolute top-1/2 left-0 size-5 -translate-y-1/2 text-ink-muted"
            aria-hidden="true"
          />
          <input
            id={`${listId}-input`}
            type="search"
            autoComplete="off"
            enterKeyHint="search"
            maxLength={100}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
            placeholder="Search rings, jhumkas, 22K…"
            className="min-h-14 w-full border-0 border-b border-line-strong bg-transparent pr-10 pl-8 font-display text-2xl placeholder:text-ink-subtle focus-visible:border-ink focus-visible:outline-none"
            aria-controls={listId}
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('');
              }}
              className="absolute top-1/2 right-0 inline-flex size-11 -translate-y-1/2 items-center justify-center text-ink-muted hover:text-ink"
              aria-label="Clear search"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          )}
        </form>

        <div id={listId} aria-live="polite" className="mt-6 min-h-24">
          {deferred.length >= 2 && suggestions.isFetching && !hasResults && (
            <Spinner label="Searching" />
          )}
          {deferred.length >= 2 && data && !hasResults && !suggestions.isFetching && (
            <p className="text-sm text-ink-muted">
              No matches for “{deferred}”. Try a category like rings or earrings, or a purity like
              22K.
            </p>
          )}
          {data && data.categories.length > 0 && (
            <div className="mb-6">
              <p className="eyebrow mb-2">Categories</p>
              <ul className="flex flex-wrap gap-2">
                {data.categories.map((c) => (
                  <li key={c.slug}>
                    <Link
                      to={`/collections/${c.slug}`}
                      onClick={close}
                      className="inline-flex min-h-9 items-center rounded-sm border border-line px-3 text-sm hover:border-ink"
                    >
                      {c.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data && data.products.length > 0 && (
            <div>
              <p className="eyebrow mb-2">Products</p>
              <ul className="divide-y divide-line">
                {data.products.map((p) => (
                  <li key={p.slug}>
                    <Link
                      to={`/products/${p.slug}`}
                      onClick={close}
                      className="flex items-center gap-4 py-3 hover:bg-surface-muted/60"
                    >
                      <span className="block size-14 shrink-0 overflow-hidden rounded-sm bg-surface-muted">
                        {p.image && (
                          <img src={p.image.url} alt="" className="h-full w-full object-cover" />
                        )}
                      </span>
                      <span className="flex-1 text-sm font-medium">{p.name}</span>
                      {p.price.amount && (
                        <span className="tabular text-sm text-ink-muted">
                          {formatMoney(p.price.amount)}
                        </span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {query.trim().length >= 2 && (
            <Link
              to={`/search?q=${encodeURIComponent(query.trim())}`}
              onClick={close}
              className="mt-6 inline-block text-sm font-medium underline decoration-gold underline-offset-4"
            >
              See all results for “{query.trim()}”
            </Link>
          )}
        </div>
      </DialogContent>
    </DialogRoot>
  );
}
