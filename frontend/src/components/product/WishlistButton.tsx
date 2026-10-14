import { Heart } from 'lucide-react';

import { useToast } from '@/components/ui/Toaster';
import { useWishlist } from '@/api/queries/wishlist';
import { cn } from '@/lib/cn';

/**
 * Save/unsave a product. Guests: stored in this browser (slugs only). Signed-in customers: saved to
 * their account (the browser list is merged in at sign-in).
 */
export function WishlistButton({
  slug,
  name,
  className,
  variant = 'icon',
}: {
  slug: string;
  name: string;
  className?: string;
  variant?: 'icon' | 'full';
}) {
  const wishlist = useWishlist();
  const { notify } = useToast();
  const saved = wishlist.has(slug);

  const toggle = () => {
    if (saved) {
      wishlist.toggle(slug, false);
      notify(`Removed ${name} from your wishlist`, 'info');
    } else {
      wishlist.toggle(slug, true);
      notify(`Saved ${name} to your wishlist`);
    }
  };

  if (variant === 'full') {
    return (
      <button
        type="button"
        onClick={toggle}
        aria-pressed={saved}
        className={cn(
          'inline-flex min-h-11 items-center justify-center gap-2 rounded-sm border border-line-strong px-5 text-sm font-medium transition-colors hover:border-ink',
          className,
        )}
      >
        <Heart className={cn('size-4', saved && 'fill-ink')} strokeWidth={1.5} aria-hidden="true" />
        {saved ? 'Saved to wishlist' : 'Save to wishlist'}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={saved}
      aria-label={saved ? `Remove ${name} from wishlist` : `Save ${name} to wishlist`}
      className={cn(
        'inline-flex size-11 items-center justify-center rounded-full bg-surface/80 text-ink backdrop-blur-sm transition-colors hover:bg-surface',
        className,
      )}
    >
      <Heart
        className={cn('size-[18px]', saved && 'fill-ink')}
        strokeWidth={1.5}
        aria-hidden="true"
      />
    </button>
  );
}
