import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router';

import type { ProductQuery, SortOption } from '@/api/queries/catalogue';

const SORTS: SortOption[] = ['relevance', 'newest', 'price_asc', 'price_desc'];
export const PAGE_SIZE = 24;

/** Keys the shopper can toggle; their values live in the URL so views are shareable. */
export type RefinementKey = 'purity' | 'metal_colour' | 'attr';

/**
 * Two-way binding between URL query parameters and the product query.
 * Changing any refinement resets to page 1.
 */
export function useProductQueryParams(base: Pick<ProductQuery, 'category' | 'collection'> = {}) {
  const [params, setParams] = useSearchParams();
  const { category: baseCategory, collection: baseCollection } = base;

  const query = useMemo<ProductQuery>(() => {
    const sortParam = params.get('sort') as SortOption | null;
    const page = Number(params.get('page') ?? '1');
    return {
      q: params.get('q') ?? undefined,
      collection: baseCollection,
      category: baseCategory ?? params.get('category') ?? undefined,
      purity: params.getAll('purity'),
      metal_colour: params.getAll('metal_colour'),
      attr: params.getAll('attr'),
      min_price: params.get('min_price') ?? undefined,
      max_price: params.get('max_price') ?? undefined,
      in_stock: params.get('in_stock') === 'true' ? true : undefined,
      sort: sortParam && SORTS.includes(sortParam) ? sortParam : 'relevance',
      page: Number.isInteger(page) && page > 0 ? page : 1,
      page_size: PAGE_SIZE,
    };
  }, [params, baseCategory, baseCollection]);

  const update = useCallback(
    (mutate: (next: URLSearchParams) => void, options: { resetPage?: boolean } = {}) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          mutate(next);
          if (options.resetPage ?? true) next.delete('page');
          return next;
        },
        { preventScrollReset: true },
      );
    },
    [setParams],
  );

  const toggleValue = useCallback(
    (key: RefinementKey | 'category', value: string) => {
      update((next) => {
        const values = next.getAll(key);
        next.delete(key);
        const updated = values.includes(value)
          ? values.filter((v) => v !== value)
          : [...values, value];
        updated.forEach((v) => {
          next.append(key, v);
        });
      });
    },
    [update],
  );

  const setValue = useCallback(
    (key: string, value: string | null, options?: { resetPage?: boolean }) => {
      update((next) => {
        if (value === null || value === '') next.delete(key);
        else next.set(key, value);
      }, options);
    },
    [update],
  );

  /** Set several keys in ONE URL update (separate calls would overwrite each other). */
  const setValues = useCallback(
    (values: Record<string, string | null>) => {
      update((next) => {
        Object.entries(values).forEach(([key, value]) => {
          if (value === null || value === '') next.delete(key);
          else next.set(key, value);
        });
      });
    },
    [update],
  );

  const clearRefinements = useCallback(() => {
    update((next) => {
      ['purity', 'metal_colour', 'attr', 'min_price', 'max_price', 'in_stock', 'category'].forEach(
        (key) => {
          next.delete(key);
        },
      );
    });
  }, [update]);

  return { query, toggleValue, setValue, setValues, clearRefinements };
}
