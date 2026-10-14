import { Search, X } from 'lucide-react';
import { useState, type SyntheticEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';

import { ApiError } from '@/api/client';
import { useCategories, useListing } from '@/api/queries/catalogue';
import { PageHeader, PageMeta } from '@/components/layout/Page';
import { ListingView } from '@/components/product/ListingView';
import { ErrorState, Skeleton } from '@/components/ui/Feedback';
import { NotFoundPage } from '@/pages/NotFoundPage';

/** /collections — everything, with category as a filter. */
export function CollectionsPage() {
  return (
    <>
      <PageMeta
        title="All jewellery"
        description="Browse rings, earrings, necklaces, pendants, bangles, bracelets, chains and mangalsutras with transparent pricing."
        path="/collections"
      />
      <ListingView
        header={
          <PageHeader
            eyebrow="Shop"
            title="All jewellery"
            crumbs={[{ label: 'Home', to: '/' }, { label: 'All jewellery' }]}
          />
        }
      />
    </>
  );
}

/** /collections/:slug — a category (e.g. rings) or a curated collection (e.g. bridal). */
export function ListingPage() {
  const { slug = '' } = useParams();
  const listing = useListing(slug);

  if (listing.isError) {
    if (listing.error instanceof ApiError && listing.error.status === 404) return <NotFoundPage />;
    return <ErrorState error={listing.error} onRetry={() => void listing.refetch()} />;
  }
  if (!listing.data) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-14 text-center sm:px-6 lg:px-8">
        <Skeleton className="mx-auto h-4 w-24" />
        <Skeleton className="mx-auto mt-4 h-12 w-72" />
      </div>
    );
  }

  const data = listing.data;
  const entity = data.kind === 'category' ? data.category : data.collection;
  if (!entity) return <NotFoundPage />;

  return (
    <>
      <PageMeta
        title={entity.seo_title ?? entity.name}
        description={entity.seo_description ?? entity.description ?? undefined}
        path={`/collections/${entity.slug}`}
      />
      <ListingView
        key={slug}
        category={data.kind === 'category' ? slug : undefined}
        collection={data.kind === 'collection' ? slug : undefined}
        header={
          <PageHeader
            eyebrow={data.kind === 'category' ? 'Category' : 'Collection'}
            title={entity.name}
            description={entity.description}
            crumbs={[
              { label: 'Home', to: '/' },
              { label: 'All jewellery', to: '/collections' },
              { label: entity.name },
            ]}
          />
        }
      />
    </>
  );
}

function SearchBox() {
  const [params, setParams] = useSearchParams();
  const [value, setValue] = useState(params.get('q') ?? '');

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    setParams((current) => {
      const next = new URLSearchParams(current);
      const q = value.trim();
      if (q) next.set('q', q);
      else next.delete('q');
      next.delete('page');
      return next;
    });
  };

  return (
    <form role="search" onSubmit={submit} className="relative mx-auto mt-8 max-w-xl">
      <label htmlFor="search-page-input" className="sr-only">
        Search jewellery
      </label>
      <Search
        className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-ink-muted"
        aria-hidden="true"
      />
      <input
        id="search-page-input"
        type="search"
        enterKeyHint="search"
        maxLength={100}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
        }}
        placeholder="Search rings, jhumkas, 22K…"
        className="min-h-13 w-full rounded-sm border border-line-strong bg-surface pr-12 pl-12 text-base focus-visible:border-ink"
      />
      {value && (
        <button
          type="button"
          onClick={() => {
            setValue('');
          }}
          className="absolute top-1/2 right-1 inline-flex size-11 -translate-y-1/2 items-center justify-center text-ink-muted hover:text-ink"
          aria-label="Clear search"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      )}
    </form>
  );
}

function SearchSuggestions() {
  const categories = useCategories();
  return (
    <>
      Check the spelling or try a broader term. Popular categories:{' '}
      {(categories.data ?? []).slice(0, 4).map((c, i, list) => (
        <span key={c.slug}>
          <Link to={`/collections/${c.slug}`} className="underline underline-offset-4">
            {c.name}
          </Link>
          {i < list.length - 1 ? ', ' : '.'}
        </span>
      ))}
    </>
  );
}

/** /search?q=… */
export function SearchPage() {
  const [params] = useSearchParams();
  const q = params.get('q')?.trim() ?? '';
  return (
    <>
      <PageMeta title={q ? `Search: ${q}` : 'Search'} path="/search" noindex />
      <ListingView
        header={
          <PageHeader eyebrow="Search" title={q ? `Results for “${q}”` : 'Search the collection'}>
            <SearchBox key={q} />
          </PageHeader>
        }
        emptyHint={<SearchSuggestions />}
      />
    </>
  );
}
