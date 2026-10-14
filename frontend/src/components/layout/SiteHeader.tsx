import { Heart, Menu, Search, ShoppingBag, UserRound } from 'lucide-react';
import { useState } from 'react';
import { Link, NavLink } from 'react-router';

import { useMe } from '@/api/queries/account';
import { useCart } from '@/api/queries/cart';
import { useCategories, usePublicSettings } from '@/api/queries/catalogue';
import { useWishlist } from '@/api/queries/wishlist';
import { IconButton } from '@/components/ui/Button';
import { DialogRoot, SheetContent } from '@/components/ui/Dialog';
import { cn } from '@/lib/cn';
import { env } from '@/lib/env';

import { Container } from './Page';
import { SearchDialog } from './SearchDialog';

const INFO_LINKS = [
  { to: '/gold-buying-guide', label: 'Gold buying guide' },
  { to: '/jewellery-care', label: 'Jewellery care' },
  { to: '/about', label: 'Our story' },
  { to: '/contact', label: 'Contact us' },
];

export function AnnouncementBar() {
  const settings = usePublicSettings();
  const announcement = settings.data?.announcement;
  if (!announcement?.enabled || !announcement.text) return null;
  return (
    <div className="bg-noir text-noir-ink">
      <Container className="flex min-h-9 items-center justify-center py-2 text-center text-xs tracking-wide">
        {announcement.link ? (
          <Link to={announcement.link} className="underline-offset-4 hover:underline">
            {announcement.text}
          </Link>
        ) : (
          <p>{announcement.text}</p>
        )}
      </Container>
    </div>
  );
}

function Logo() {
  return (
    <Link
      to="/"
      className="font-display text-2xl font-medium tracking-[0.22em] uppercase sm:text-[1.7rem]"
      aria-label={`${env.storeName} — home`}
    >
      {env.storeName}
    </Link>
  );
}

function AccountLink() {
  const me = useMe();
  const signedIn = Boolean(me.data);
  return (
    <Link
      to={signedIn ? '/account' : '/login'}
      className="inline-flex size-11 items-center justify-center rounded-sm hover:bg-surface-muted"
      aria-label={signedIn ? 'My account' : 'Sign in'}
      title={signedIn ? 'My account' : 'Sign in'}
    >
      <UserRound className="size-5" strokeWidth={1.5} aria-hidden="true" />
    </Link>
  );
}

function CartLink() {
  const cart = useCart();
  const count = cart.data?.item_count ?? 0;
  return (
    <Link
      to="/cart"
      className="relative inline-flex size-11 items-center justify-center rounded-sm hover:bg-surface-muted"
      aria-label={count ? `Cart, ${count} ${count === 1 ? 'item' : 'items'}` : 'Cart'}
      title="Cart"
    >
      <ShoppingBag className="size-5" strokeWidth={1.5} aria-hidden="true" />
      {count > 0 && (
        <span
          aria-hidden="true"
          className="tabular absolute top-1.5 right-1 flex size-4 items-center justify-center rounded-full bg-ink text-[10px] text-ivory"
        >
          {count > 9 ? '9+' : count}
        </span>
      )}
      {/* Announce changes to the cart count to screen-reader users. */}
      <span className="sr-only" aria-live="polite">
        {cart.isFetched ? `${count} ${count === 1 ? 'item' : 'items'} in cart` : ''}
      </span>
    </Link>
  );
}

function WishlistLink() {
  const { slugs: items } = useWishlist();
  return (
    <Link
      to="/wishlist"
      className="relative inline-flex size-11 items-center justify-center rounded-sm hover:bg-surface-muted"
      aria-label={items.length ? `Wishlist, ${items.length} saved` : 'Wishlist'}
      title="Wishlist"
    >
      <Heart className="size-5" strokeWidth={1.5} aria-hidden="true" />
      {items.length > 0 && (
        <span
          aria-hidden="true"
          className="tabular absolute top-1.5 right-1.5 flex size-4 items-center justify-center rounded-full bg-ink text-[10px] text-ivory"
        >
          {items.length > 9 ? '9+' : items.length}
        </span>
      )}
    </Link>
  );
}

export function SiteHeader() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const categories = useCategories();
  const topCategories = (categories.data ?? []).filter((c) => !c.parent_slug);

  const navLink = ({ isActive }: { isActive: boolean }) =>
    cn(
      'relative py-3 text-xs font-medium tracking-[0.16em] uppercase transition-colors hover:text-ink',
      isActive
        ? 'text-ink after:absolute after:inset-x-0 after:bottom-1.5 after:h-px after:bg-gold'
        : 'text-ink-muted',
    );

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-ivory/95 backdrop-blur supports-[backdrop-filter]:bg-ivory/85">
      <Container className="grid h-16 grid-cols-[1fr_auto_1fr] items-center lg:h-20">
        <div className="flex items-center gap-1">
          <IconButton
            label="Open menu"
            className="-ml-2 lg:hidden"
            onClick={() => {
              setMenuOpen(true);
            }}
          >
            <Menu className="size-5" strokeWidth={1.5} aria-hidden="true" />
          </IconButton>
          <button
            type="button"
            onClick={() => {
              setSearchOpen(true);
            }}
            className="hidden min-h-11 items-center gap-2 rounded-sm pr-3 text-sm text-ink-muted hover:text-ink lg:inline-flex"
          >
            <Search className="size-[18px]" strokeWidth={1.5} aria-hidden="true" />
            Search
          </button>
        </div>
        <Logo />
        <div className="flex items-center justify-end gap-0.5">
          <IconButton
            label="Search"
            className="lg:hidden"
            onClick={() => {
              setSearchOpen(true);
            }}
          >
            <Search className="size-5" strokeWidth={1.5} aria-hidden="true" />
          </IconButton>
          <AccountLink />
          <WishlistLink />
          <CartLink />
        </div>
      </Container>

      <nav aria-label="Main" className="hidden border-t border-line/60 lg:block">
        <Container>
          <ul className="flex items-center justify-center gap-8">
            <li>
              <NavLink to="/collections" end className={navLink}>
                All jewellery
              </NavLink>
            </li>
            {topCategories.map((category) => (
              <li key={category.slug}>
                <NavLink to={`/collections/${category.slug}`} className={navLink}>
                  {category.name}
                </NavLink>
              </li>
            ))}
            <li>
              <NavLink to="/gold-buying-guide" className={navLink}>
                Buying guide
              </NavLink>
            </li>
          </ul>
        </Container>
      </nav>

      <SearchDialog open={searchOpen} onOpenChange={setSearchOpen} />

      <DialogRoot open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent title="Menu" side="left">
          <nav aria-label="Mobile">
            <ul className="divide-y divide-line px-5">
              <li>
                <Link
                  to="/collections"
                  onClick={() => {
                    setMenuOpen(false);
                  }}
                  className="flex min-h-13 items-center font-display text-xl"
                >
                  All jewellery
                </Link>
              </li>
              {topCategories.map((category) => (
                <li key={category.slug}>
                  <Link
                    to={`/collections/${category.slug}`}
                    onClick={() => {
                      setMenuOpen(false);
                    }}
                    className="flex min-h-13 items-center font-display text-xl"
                  >
                    {category.name}
                  </Link>
                </li>
              ))}
            </ul>
            <ul className="mt-6 space-y-1 border-t border-line px-5 pt-6">
              {[
                { to: '/account', label: 'My account' },
                { to: '/wishlist', label: 'Wishlist' },
                ...INFO_LINKS,
              ].map((link) => (
                <li key={link.to}>
                  <Link
                    to={link.to}
                    onClick={() => {
                      setMenuOpen(false);
                    }}
                    className="flex min-h-11 items-center text-sm text-ink-muted hover:text-ink"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </SheetContent>
      </DialogRoot>
    </header>
  );
}
