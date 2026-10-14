import { X } from 'lucide-react';
import { useId, useState, type SyntheticEvent } from 'react';

import type { ProductQuery, SortOption } from '@/api/queries/catalogue';
import type { Facets } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Accordion, AccordionItem, Checkbox } from '@/components/ui/Disclosure';
import { Select } from '@/components/ui/Field';
import type { useProductQueryParams } from '@/hooks/useProductQueryParams';
import { cn } from '@/lib/cn';
import { formatMoney } from '@/lib/format';

type Controls = ReturnType<typeof useProductQueryParams>;

const ATTRIBUTE_TITLES: Record<string, string> = { occasion: 'Occasion', style: 'Style' };

export const SORT_LABELS: Record<SortOption, string> = {
  relevance: 'Recommended',
  newest: 'Newest',
  price_asc: 'Price: low to high',
  price_desc: 'Price: high to low',
};

export function SortSelect({ query, controls }: { query: ProductQuery; controls: Controls }) {
  const id = useId();
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-sm whitespace-nowrap text-ink-muted">
        Sort by
      </label>
      <Select
        id={id}
        value={query.sort ?? 'relevance'}
        onChange={(e) => {
          controls.setValue('sort', e.target.value === 'relevance' ? null : e.target.value);
        }}
        className="min-h-10 w-auto py-1.5 text-sm"
      >
        {(Object.keys(SORT_LABELS) as SortOption[]).map((sort) => (
          <option key={sort} value={sort}>
            {query.q && sort === 'relevance' ? 'Best match' : SORT_LABELS[sort]}
          </option>
        ))}
      </Select>
    </div>
  );
}

function PriceFilter({
  query,
  controls,
  facets,
}: {
  query: ProductQuery;
  controls: Controls;
  facets?: Facets;
}) {
  const [min, setMin] = useState(query.min_price ?? '');
  const [max, setMax] = useState(query.max_price ?? '');
  const id = useId();
  const apply = (event: SyntheticEvent) => {
    event.preventDefault();
    controls.setValues({ min_price: min.trim() || null, max_price: max.trim() || null });
  };
  return (
    <form onSubmit={apply} className="space-y-3">
      {facets?.price_min && facets.price_max && (
        <p className="text-xs text-ink-subtle">
          From {formatMoney(facets.price_min)} to {formatMoney(facets.price_max)}
        </p>
      )}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label htmlFor={`${id}-min`} className="text-xs text-ink-muted">
            Min (₹)
          </label>
          <input
            id={`${id}-min`}
            inputMode="numeric"
            pattern="[0-9]*"
            value={min}
            onChange={(e) => {
              setMin(e.target.value.replace(/[^0-9]/g, ''));
            }}
            className="mt-1 min-h-10 w-full rounded-sm border border-line-strong bg-surface px-2.5 text-sm"
          />
        </div>
        <div className="flex-1">
          <label htmlFor={`${id}-max`} className="text-xs text-ink-muted">
            Max (₹)
          </label>
          <input
            id={`${id}-max`}
            inputMode="numeric"
            pattern="[0-9]*"
            value={max}
            onChange={(e) => {
              setMax(e.target.value.replace(/[^0-9]/g, ''));
            }}
            className="mt-1 min-h-10 w-full rounded-sm border border-line-strong bg-surface px-2.5 text-sm"
          />
        </div>
      </div>
      <Button type="submit" size="sm" variant="secondary" className="w-full">
        Apply price
      </Button>
    </form>
  );
}

export function FilterPanel({
  query,
  facets,
  controls,
  showCategories,
}: {
  query: ProductQuery;
  facets?: Facets;
  controls: Controls;
  showCategories: boolean;
}) {
  const id = useId();
  const attributeKeys = Object.keys(facets?.attributes ?? {});
  return (
    <Accordion defaultValue={['category', 'purity', 'price', 'availability']}>
      {showCategories && facets && facets.categories.length > 0 && (
        <AccordionItem value="category" title="Category">
          <ul className="space-y-0.5">
            {facets.categories.map((c) => {
              const active = query.category === c.value;
              return (
                <li key={c.value}>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => {
                      controls.setValue('category', active ? null : c.value);
                    }}
                    className={cn(
                      'flex min-h-9 w-full items-center justify-between text-left text-sm hover:text-ink',
                      active ? 'font-medium text-ink' : 'text-ink-muted',
                    )}
                  >
                    <span>{c.label}</span>
                    <span className="tabular text-ink-subtle">{c.count}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </AccordionItem>
      )}
      {facets && facets.purities.length > 0 && (
        <AccordionItem value="purity" title="Purity">
          {facets.purities.map((f) => (
            <Checkbox
              key={f.value}
              id={`${id}-purity-${f.value}`}
              label={f.label}
              count={f.count}
              checked={query.purity?.includes(f.value) ?? false}
              onCheckedChange={() => {
                controls.toggleValue('purity', f.value);
              }}
            />
          ))}
        </AccordionItem>
      )}
      {facets && facets.metal_colours.length > 0 && (
        <AccordionItem value="metal" title="Metal colour">
          {facets.metal_colours.map((f) => (
            <Checkbox
              key={f.value}
              id={`${id}-metal-${f.value}`}
              label={f.label}
              count={f.count}
              checked={query.metal_colour?.includes(f.value) ?? false}
              onCheckedChange={() => {
                controls.toggleValue('metal_colour', f.value);
              }}
            />
          ))}
        </AccordionItem>
      )}
      <AccordionItem value="price" title="Price">
        <PriceFilter
          key={`${query.min_price ?? ''}-${query.max_price ?? ''}`}
          query={query}
          controls={controls}
          facets={facets}
        />
      </AccordionItem>
      <AccordionItem value="availability" title="Availability">
        <Checkbox
          id={`${id}-in-stock`}
          label="In stock only"
          count={facets?.in_stock_count}
          checked={query.in_stock ?? false}
          onCheckedChange={(checked) => {
            controls.setValue('in_stock', checked ? 'true' : null);
          }}
        />
      </AccordionItem>
      {attributeKeys.map((key) => (
        <AccordionItem key={key} value={`attr-${key}`} title={ATTRIBUTE_TITLES[key] ?? key}>
          {(facets?.attributes[key] ?? []).map((f) => {
            const token = `${key}:${f.value}`;
            return (
              <Checkbox
                key={token}
                id={`${id}-${key}-${f.value}`}
                label={f.label}
                count={f.count}
                checked={query.attr?.includes(token) ?? false}
                onCheckedChange={() => {
                  controls.toggleValue('attr', token);
                }}
              />
            );
          })}
        </AccordionItem>
      ))}
    </Accordion>
  );
}

interface Chip {
  label: string;
  remove: () => void;
}

export function activeChips(
  query: ProductQuery,
  controls: Controls,
  facets?: Facets,
  showCategory = true,
): Chip[] {
  const chips: Chip[] = [];
  if (showCategory && query.category) {
    const label =
      facets?.categories.find((c) => c.value === query.category)?.label ?? query.category;
    chips.push({
      label,
      remove: () => {
        controls.setValue('category', null);
      },
    });
  }
  query.purity?.forEach((p) => {
    chips.push({
      label: p,
      remove: () => {
        controls.toggleValue('purity', p);
      },
    });
  });
  query.metal_colour?.forEach((m) => {
    const label = facets?.metal_colours.find((f) => f.value === m)?.label ?? m;
    chips.push({
      label,
      remove: () => {
        controls.toggleValue('metal_colour', m);
      },
    });
  });
  query.attr?.forEach((token) => {
    const value = token.split(':')[1] ?? token;
    chips.push({
      label: value.charAt(0).toUpperCase() + value.slice(1),
      remove: () => {
        controls.toggleValue('attr', token);
      },
    });
  });
  if (query.min_price || query.max_price) {
    const label =
      query.min_price && query.max_price
        ? `${formatMoney(query.min_price)} – ${formatMoney(query.max_price)}`
        : query.min_price
          ? `From ${formatMoney(query.min_price)}`
          : `Up to ${formatMoney(query.max_price)}`;
    chips.push({
      label,
      remove: () => {
        controls.setValues({ min_price: null, max_price: null });
      },
    });
  }
  if (query.in_stock)
    chips.push({
      label: 'In stock',
      remove: () => {
        controls.setValue('in_stock', null);
      },
    });
  return chips;
}

export function ActiveFilters({ chips, onClearAll }: { chips: Chip[]; onClearAll: () => void }) {
  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Active filters" role="group">
      {chips.map((chip) => (
        <button
          key={chip.label}
          type="button"
          onClick={chip.remove}
          className="inline-flex min-h-9 items-center gap-1.5 rounded-sm bg-gold-soft px-3 text-sm text-ink hover:bg-gold-soft/70"
          aria-label={`Remove filter: ${chip.label}`}
        >
          {chip.label}
          <X className="size-3.5" aria-hidden="true" />
        </button>
      ))}
      <button
        type="button"
        onClick={onClearAll}
        className="min-h-9 px-2 text-sm text-ink-muted underline underline-offset-4 hover:text-ink"
      >
        Clear all
      </button>
    </div>
  );
}
