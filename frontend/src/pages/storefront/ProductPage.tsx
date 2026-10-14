import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';

import { ApiError } from '@/api/client';
import { useProduct, useProducts, useRelated } from '@/api/queries/catalogue';
import type { ProductDetail } from '@/api/types';
import { Breadcrumbs, Container, PageMeta } from '@/components/layout/Page';
import { AddToCart } from '@/components/product/AddToCart';
import { ProductGrid } from '@/components/product/ProductCard';
import {
  PincodeChecker,
  PriceBreakdown,
  ProductJsonLd,
  SpecList,
  StockStatusLine,
  VariantPicker,
} from '@/components/product/ProductDetails';
import { ProductGallery } from '@/components/product/ProductGallery';
import { WishlistButton } from '@/components/product/WishlistButton';
import { Accordion, AccordionItem } from '@/components/ui/Disclosure';
import { Alert, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { Price } from '@/components/ui/Price';
import { RECENTLY_VIEWED_KEY, useLocalList } from '@/hooks/useLocalList';
import { env } from '@/lib/env';
import { NotFoundPage } from '@/pages/NotFoundPage';

function ProductSkeleton() {
  return (
    <Container className="grid gap-10 py-10 lg:grid-cols-2">
      <Skeleton className="aspect-4/5 w-full" />
      <div className="space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-12 w-3/4" />
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-24 w-full" />
      </div>
    </Container>
  );
}

function RecentlyViewed({ currentSlug }: { currentSlug: string }) {
  const { items } = useLocalList(RECENTLY_VIEWED_KEY, 12);
  const slugs = items.filter((s) => s !== currentSlug).slice(0, 8);
  const products = useProducts({ slug: slugs, page_size: 8 }, { enabled: slugs.length > 0 });
  const ordered = useMemo(() => {
    const bySlug = new Map((products.data?.items ?? []).map((p) => [p.slug, p]));
    return slugs.flatMap((s) => bySlug.get(s) ?? []);
  }, [products.data, slugs]);
  if (slugs.length === 0 || ordered.length === 0) return null;
  return (
    <section aria-labelledby="recently-viewed" className="border-t border-line py-16">
      <h2 id="recently-viewed" className="mb-8 font-display text-3xl">
        Recently viewed
      </h2>
      <ProductGrid products={ordered.slice(0, 4)} />
    </section>
  );
}

function ProductView({ product }: { product: ProductDetail }) {
  const defaultVariant = product.variants.find((v) => v.is_default) ?? product.variants[0];
  const [variantId, setVariantId] = useState(defaultVariant?.id ?? '');
  const variant = product.variants.find((v) => v.id === variantId) ?? defaultVariant;
  const related = useRelated(product.slug);
  const recent = useLocalList(RECENTLY_VIEWED_KEY, 12);
  const { add: addRecent } = recent;

  useEffect(() => {
    addRecent(product.slug, { toFront: true });
  }, [product.slug, addRecent]);

  const crumbs = [
    { label: 'Home', to: '/' },
    ...(product.parent_category
      ? [
          {
            label: product.parent_category.name,
            to: `/collections/${product.parent_category.slug}`,
          },
        ]
      : []),
    { label: product.category.name, to: `/collections/${product.category.slug}` },
    { label: product.name },
  ];
  const path = `/products/${product.slug}`;

  if (!variant) {
    return (
      <Container className="py-16">
        <Alert tone="info" title="This piece is not currently available." />
      </Container>
    );
  }

  return (
    <>
      <PageMeta
        title={product.seo_title ?? product.name}
        description={product.seo_description ?? product.description ?? undefined}
        path={path}
        image={product.images[0]?.url}
      />
      <ProductJsonLd product={product} variant={variant} url={`${env.siteUrl}${path}`} />
      <Container className="pt-6 pb-32 lg:pb-16">
        <Breadcrumbs items={crumbs} />
        <div className="mt-6 grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
          <ProductGallery images={product.images} name={product.name} />

          <div className="lg:sticky lg:top-32 lg:self-start">
            <p className="eyebrow">
              {product.purity} {product.category.name.replace(/s$/, '')}
            </p>
            <h1 className="mt-3 font-display text-4xl leading-tight font-medium tracking-tight sm:text-5xl">
              {product.name}
            </h1>
            {product.is_sample && (
              <p className="mt-3 text-xs text-gold-deep">
                Sample product for development — not real inventory.
              </p>
            )}

            <div className="mt-6" aria-live="polite">
              <Price price={variant.price} size="lg" />
              {variant.price.available && (
                <p className="mt-1 text-xs text-ink-muted">
                  Incl. of all taxes
                  {variant.price.discount_label ? ` · ${variant.price.discount_label}` : ''}
                </p>
              )}
            </div>

            <div className="mt-8 space-y-6">
              <VariantPicker
                variants={product.variants}
                selectedId={variant.id}
                onSelect={setVariantId}
              />
              <StockStatusLine
                status={variant.stock_status}
                quantity={variant.available_quantity}
              />
              <div className="space-y-3">
                <AddToCart key={variant.id} product={product} variant={variant} />
                <WishlistButton
                  slug={product.slug}
                  name={product.name}
                  variant="full"
                  className="w-full"
                />
              </div>
            </div>

            <div className="mt-8 rounded-md border border-line bg-surface p-5">
              <h2 className="text-sm font-medium">Check delivery</h2>
              <div className="mt-3">
                <PincodeChecker />
              </div>
            </div>

            <Accordion className="mt-8" defaultValue={['price']}>
              <AccordionItem value="price" title="Price breakdown">
                <PriceBreakdown price={variant.price} />
              </AccordionItem>
              {product.description && (
                <AccordionItem value="description" title="Description">
                  <p>{product.description}</p>
                </AccordionItem>
              )}
              <AccordionItem value="specs" title="Specifications">
                <SpecList product={product} variant={variant} />
                {product.stone_details && <p className="mt-4">{product.stone_details}</p>}
              </AccordionItem>
              {(product.hallmark_details || product.certification_details) && (
                <AccordionItem value="hallmark" title="Hallmark & certification">
                  {product.hallmark_details && <p>{product.hallmark_details}</p>}
                  {product.certification_details && (
                    <p className="mt-2">{product.certification_details}</p>
                  )}
                </AccordionItem>
              )}
              {product.care_instructions && (
                <AccordionItem value="care" title="Care">
                  <p>{product.care_instructions}</p>
                  <Link
                    to="/jewellery-care"
                    className="mt-2 inline-block underline underline-offset-4"
                  >
                    Read the full care guide
                  </Link>
                </AccordionItem>
              )}
              <AccordionItem value="returns" title="Returns, exchanges & shipping">
                <ul className="list-disc space-y-1 pl-5">
                  <li>
                    {product.return_eligible
                      ? `Returns accepted within ${product.return_window_days ?? '—'} days of delivery.`
                      : 'This piece is not eligible for return.'}
                  </li>
                  <li>
                    {product.exchange_eligible
                      ? 'Eligible for exchange.'
                      : 'This piece is not eligible for exchange.'}
                  </li>
                </ul>
                <p className="mt-3">
                  See our{' '}
                  <Link to="/returns-and-exchanges" className="underline underline-offset-4">
                    returns policy
                  </Link>{' '}
                  and{' '}
                  <Link to="/shipping-policy" className="underline underline-offset-4">
                    shipping policy
                  </Link>
                  .
                </p>
              </AccordionItem>
            </Accordion>
          </div>
        </div>

        {related.data && related.data.length > 0 && (
          <section aria-labelledby="related" className="mt-20 border-t border-line pt-16">
            <h2 id="related" className="mb-8 font-display text-3xl">
              You may also like
            </h2>
            <ProductGrid products={related.data.slice(0, 4)} />
          </section>
        )}
        <div className="mt-16">
          <RecentlyViewed currentSlug={product.slug} />
        </div>
      </Container>
    </>
  );
}

export function ProductPage() {
  const { slug = '' } = useParams();
  const product = useProduct(slug);
  if (product.isPending) return <ProductSkeleton />;
  if (product.isError) {
    if (product.error instanceof ApiError && product.error.status === 404) return <NotFoundPage />;
    return <ErrorState error={product.error} onRetry={() => void product.refetch()} />;
  }
  return <ProductView key={product.data.slug} product={product.data} />;
}
