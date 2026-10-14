import { Heart } from 'lucide-react';
import { useMemo } from 'react';
import { Link } from 'react-router';

import { useProducts } from '@/api/queries/catalogue';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { ProductGrid } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/Button';
import { EmptyState, ErrorState } from '@/components/ui/Feedback';
import { GUEST_WISHLIST_KEY, useLocalList } from '@/hooks/useLocalList';

/**
 * Guest wishlist (saved in this browser). Signed-in customers get a server-side wishlist
 * (Phase 4) and this list is merged into it at sign-in.
 */
export function WishlistPage() {
  const wishlist = useLocalList(GUEST_WISHLIST_KEY);
  const slugs = wishlist.items.slice(0, 48);
  const products = useProducts({ slug: slugs, page_size: 48 }, { enabled: slugs.length > 0 });

  const ordered = useMemo(() => {
    const bySlug = new Map((products.data?.items ?? []).map((p) => [p.slug, p]));
    return slugs.flatMap((s) => bySlug.get(s) ?? []);
  }, [products.data, slugs]);

  return (
    <>
      <PageMeta title="Wishlist" path="/wishlist" noindex />
      <Container className="pb-20">
        <PageHeader
          eyebrow="Saved pieces"
          title="Your wishlist"
          description="Saved on this device. Current prices and availability are shown below."
        />
        {slugs.length === 0 ? (
          <EmptyState
            icon={Heart}
            title="Nothing saved yet"
            action={
              <Button asChild>
                <Link to="/collections">Explore the collection</Link>
              </Button>
            }
          >
            Tap the heart on any piece to keep it here.
          </EmptyState>
        ) : products.isError ? (
          <ErrorState error={products.error} onRetry={() => void products.refetch()} />
        ) : (
          <>
            <ProductGrid
              products={products.data ? ordered : undefined}
              loading={products.isPending}
              skeletonCount={Math.min(slugs.length, 8)}
            />
            {products.data && ordered.length < slugs.length && (
              <p className="mt-8 text-sm text-ink-muted">
                Some saved pieces are no longer available and are not shown.
              </p>
            )}
            <div className="mt-10">
              <Button variant="link" onClick={wishlist.clear}>
                Clear wishlist
              </Button>
            </div>
          </>
        )}
      </Container>
    </>
  );
}
