import { Link } from 'react-router';

import type { ProductCard as ProductCardData } from '@/api/types';
import { Badge, Skeleton } from '@/components/ui/Feedback';
import { Price } from '@/components/ui/Price';
import { cn } from '@/lib/cn';
import { formatWeight } from '@/lib/format';

import { ProductImage } from './ProductImage';
import { WishlistButton } from './WishlistButton';

export function stockLabel(status: ProductCardData['stock_status']): string | null {
  if (status === 'out_of_stock') return 'Out of stock';
  if (status === 'low_stock') return 'Only a few left';
  return null;
}

export function ProductCard({
  product,
  priority = false,
}: {
  product: ProductCardData;
  priority?: boolean;
}) {
  const stock = stockLabel(product.stock_status);
  const href = `/products/${product.slug}`;
  return (
    <article className="group relative">
      <div className="relative aspect-4/5 overflow-hidden rounded-sm bg-surface-muted">
        {product.image && (
          <ProductImage
            image={product.image}
            priority={priority}
            sizes="(min-width: 1280px) 22vw, (min-width: 1024px) 30vw, 48vw"
            className={cn(
              'h-full w-full object-cover transition-opacity duration-500',
              product.hover_image && 'group-hover:opacity-0',
            )}
          />
        )}
        {product.hover_image && (
          <ProductImage
            image={product.hover_image}
            sizes="(min-width: 1280px) 22vw, (min-width: 1024px) 30vw, 48vw"
            className="absolute inset-0 hidden h-full w-full object-cover opacity-0 transition-opacity duration-500 group-hover:opacity-100 lg:block"
          />
        )}
        <div className="pointer-events-none absolute top-3 left-3 flex flex-col items-start gap-1.5">
          {product.is_new && (
            <Badge tone="neutral" className="bg-surface/90">
              New
            </Badge>
          )}
          {product.is_sample && <Badge tone="gold">Sample</Badge>}
        </div>
        <WishlistButton
          slug={product.slug}
          name={product.name}
          className="absolute top-2 right-2 z-10"
        />
      </div>
      <div className="mt-4 space-y-1">
        <h3 className="text-sm leading-snug font-medium sm:text-base">
          <Link
            to={href}
            className="after:absolute after:inset-0 after:content-[''] hover:underline hover:decoration-gold hover:underline-offset-4"
          >
            {product.name}
          </Link>
        </h3>
        <p className="text-xs text-ink-muted sm:text-sm">
          {product.purity}
          {product.weight_g ? ` · ${formatWeight(product.weight_g)}` : ''}
        </p>
        <div className="flex items-baseline gap-1.5">
          {product.price_is_from && product.price.available && (
            <span className="text-xs text-ink-muted">From</span>
          )}
          <Price price={product.price} size="sm" />
        </div>
        {stock && (
          <p
            className={cn(
              'text-xs',
              product.stock_status === 'out_of_stock' ? 'text-danger' : 'text-warning',
            )}
          >
            {stock}
          </p>
        )}
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <div>
      <Skeleton className="aspect-4/5 w-full" />
      <Skeleton className="mt-4 h-4 w-3/4" />
      <Skeleton className="mt-2 h-3 w-1/3" />
      <Skeleton className="mt-2 h-4 w-1/2" />
    </div>
  );
}

export function ProductGrid({
  products,
  loading = false,
  skeletonCount = 8,
  className,
}: {
  products?: ProductCardData[];
  loading?: boolean;
  skeletonCount?: number;
  className?: string;
}) {
  const grid = cn(
    'grid grid-cols-2 gap-x-4 gap-y-10 sm:gap-x-6 lg:grid-cols-3 lg:gap-y-12 xl:grid-cols-4',
    className,
  );
  if (loading || !products) {
    return (
      <div className={grid} aria-busy="true" aria-label="Loading products">
        {Array.from({ length: skeletonCount }, (_, i) => (
          <ProductCardSkeleton key={i} />
        ))}
      </div>
    );
  }
  return (
    <ul className={grid}>
      {products.map((product, index) => (
        <li key={product.id}>
          <ProductCard product={product} priority={index < 4} />
        </li>
      ))}
    </ul>
  );
}
