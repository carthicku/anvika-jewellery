import { Heart } from 'lucide-react';
import { useMemo } from 'react';
import { Link, Navigate } from 'react-router';

import { useMe } from '@/api/queries/account';
import { useProducts } from '@/api/queries/catalogue';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { ProductGrid } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/Button';
import { EmptyState, ErrorState } from '@/components/ui/Feedback';
import { GUEST_WISHLIST_KEY, useLocalList } from '@/hooks/useLocalList';

/**
 * Guest wishlist (saved in this browser). Signed-in customers are sent to /account/wishlist; this
 * browser list is merged into their account when they sign in.
 */
export function WishlistPage() {
  const me = useMe();
  const wishlist = useLocalList(GUEST_WISHLIST_KEY);
  const slugs = wishlist.items.slice(0, 48);
  const products = useProducts({ slug: slugs, page_size: 48 }, { enabled: slugs.length > 0 });

  const ordered = useMemo(() => {
    const bySlug = new Map((products.data?.items ?? []).map((p) => [p.slug, p]));
    return slugs.flatMap((s) => bySlug.get(s) ?? []);
  }, [products.data, slugs]);

  if (me.data) return <Navigate to="/account/wishlist" replace />;

  return (
    <>
      <PageMeta title="Wishlist" path="/wishlist" noindex />
      <Container className="pb-20">
        <PageHeader
          eyebrow="Saved pieces"
          title="Your wishlist"
          description={
            <>
              Saved on this device.{' '}
              <Link to="/login?next=/account/wishlist" className="underline underline-offset-4">
                Sign in
              </Link>{' '}
              to keep your wishlist on every device.
            </>
          }
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
              heading="Saved pieces"
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
