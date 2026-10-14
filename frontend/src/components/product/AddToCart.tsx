import { ShoppingBag } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';

import { ApiError } from '@/api/client';
import { useAddToCart } from '@/api/queries/cart';
import type { ProductDetail, Variant } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { QuantityStepper } from '@/components/ui/QuantityStepper';
import { useToast } from '@/components/ui/Toaster';
import { formatMoney } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

/**
 * Quantity + "Add to cart" + "Buy now". The backend re-checks stock and price on every add; the
 * quantity limit shown here is only a convenience.
 */
export function AddToCart({ product, variant }: { product: ProductDetail; variant: Variant }) {
  const [quantity, setQuantity] = useState(1);
  const add = useAddToCart();
  const { notify } = useToast();
  const navigate = useNavigate();
  const soldOut = variant.stock_status === 'out_of_stock';
  const unpriced = !variant.price.available;
  const disabled = soldOut || unpriced;
  const max = Math.max(1, variant.available_quantity);

  const submit = (thenCheckout: boolean) => {
    add.mutate(
      { variant_id: variant.id, quantity: Math.min(quantity, max) },
      {
        onSuccess: () => {
          if (thenCheckout) {
            void navigate('/cart');
          } else {
            notify(
              `Added ${product.name}${variant.size ? ` (${variant.label})` : ''} to your cart`,
            );
          }
        },
        onError: (error) => {
          notify(
            error instanceof ApiError && error.code === 'OUT_OF_STOCK'
              ? `Sorry — ${error.message}`
              : errorMessage(error),
            'error',
          );
        },
      },
    );
  };

  if (disabled) {
    return (
      <p className="text-sm text-ink-muted">
        {soldOut
          ? 'This size is currently out of stock. Save it to your wishlist and check back soon.'
          : 'This piece can’t be ordered online right now. Please contact us.'}
      </p>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <QuantityStepper
          label="Quantity"
          value={Math.min(quantity, max)}
          max={max}
          onChange={setQuantity}
        />
        <Button
          size="lg"
          className="flex-1"
          loading={add.isPending}
          onClick={() => {
            submit(false);
          }}
        >
          <ShoppingBag className="size-4" aria-hidden="true" />
          Add to cart
        </Button>
      </div>
      <Button
        size="lg"
        variant="secondary"
        className="w-full"
        disabled={add.isPending}
        onClick={() => {
          submit(true);
        }}
      >
        Buy now
      </Button>

      {/* Mobile: keep the main action within reach while reading the details below. */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-ivory/95 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur lg:hidden">
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{product.name}</p>
            {variant.price.amount && (
              <p className="tabular text-sm text-ink-muted">{formatMoney(variant.price.amount)}</p>
            )}
          </div>
          <Button
            loading={add.isPending}
            onClick={() => {
              submit(false);
            }}
            aria-label={`Add ${product.name} to cart`}
          >
            Add to cart
          </Button>
        </div>
      </div>
      <p className="text-xs text-ink-muted">
        Secure checkout. Prices are confirmed in your{' '}
        <Link to="/cart" className="underline underline-offset-2">
          cart
        </Link>{' '}
        before you pay.
      </p>
    </>
  );
}
