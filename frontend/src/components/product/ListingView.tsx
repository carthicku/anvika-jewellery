import { SearchX, SlidersHorizontal } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { useFacets, useProducts } from '@/api/queries/catalogue';
import { Container } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { DialogRoot, SheetContent } from '@/components/ui/Dialog';
import { EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Pagination } from '@/components/ui/Pagination';
import { useProductQueryParams } from '@/hooks/useProductQueryParams';

import { ActiveFilters, activeChips, FilterPanel, SortSelect } from './Filters';
import { ProductGrid } from './ProductCard';

/**
 * Product listing with URL-driven filters, sort and pagination. Used by /collections,
 * /collections/:slug and /search.
 */
export function ListingView({
  category,
  collection,
  header,
  emptyHint,
}: {
  category?: string;
  collection?: string;
  header: ReactNode;
  emptyHint?: ReactNode;
}) {
  const controls = useProductQueryParams({ category, collection });
  const { query } = controls;
  const products = useProducts(query);
  const facets = useFacets(query);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const showCategories = !category;
  const chips = activeChips(query, controls, facets.data, showCategories);

  const panel = (
    <FilterPanel
      query={query}
      facets={facets.data}
      controls={controls}
      showCategories={showCategories}
    />
  );

  const total = products.data?.total;

  return (
    <Container>
      {header}
      <div className="lg:grid lg:grid-cols-[15rem_1fr] lg:gap-12">
        <aside aria-label="Filters" className="hidden lg:block">
          <div className="sticky top-36">{panel}</div>
        </aside>

        <div>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
            <p className="text-sm text-ink-muted" aria-live="polite">
              {total === undefined ? ' ' : `${total} ${total === 1 ? 'piece' : 'pieces'}`}
            </p>
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                className="lg:hidden"
                onClick={() => {
                  setFiltersOpen(true);
                }}
              >
                <SlidersHorizontal className="size-4" aria-hidden="true" />
                Filters{chips.length ? ` (${chips.length})` : ''}
              </Button>
              <SortSelect query={query} controls={controls} />
            </div>
          </div>

          <div className="mb-6">
            <ActiveFilters chips={chips} onClearAll={controls.clearRefinements} />
          </div>

          {products.isError ? (
            <ErrorState error={products.error} onRetry={() => void products.refetch()} />
          ) : products.data && products.data.items.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title="No pieces match"
              action={
                chips.length > 0 ? (
                  <Button variant="secondary" onClick={controls.clearRefinements}>
                    Clear filters
                  </Button>
                ) : (
                  <Button asChild variant="secondary">
                    <Link to="/collections">Browse all jewellery</Link>
                  </Button>
                )
              }
            >
              {emptyHint ?? 'Try removing a filter or two to see more of the collection.'}
            </EmptyState>
          ) : (
            <div
              aria-busy={products.isFetching || undefined}
              className={products.isPlaceholderData ? 'opacity-60 transition-opacity' : undefined}
            >
              <ProductGrid products={products.data?.items} loading={products.isPending} />
              {products.data && (
                <Pagination page={products.data.page} pages={products.data.pages} />
              )}
            </div>
          )}
        </div>
      </div>

      <DialogRoot open={filtersOpen} onOpenChange={setFiltersOpen}>
        <SheetContent title="Filters" side="right">
          <div className="px-5 py-2">{panel}</div>
          <div className="sticky bottom-0 border-t border-line bg-ivory p-4">
            <Button
              className="w-full"
              onClick={() => {
                setFiltersOpen(false);
              }}
            >
              Show {total ?? ''} {total === 1 ? 'piece' : 'pieces'}
            </Button>
          </div>
        </SheetContent>
      </DialogRoot>
    </Container>
  );
}
