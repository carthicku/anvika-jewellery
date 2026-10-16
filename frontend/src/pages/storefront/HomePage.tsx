import { ArrowRight, BookOpen, MapPin, Receipt, ShieldCheck, Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { useHome } from '@/api/queries/catalogue';
import type { ProductCard as ProductCardData } from '@/api/types';
import { Container, PageMeta } from '@/components/layout/Page';
import { ProductGrid } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/Button';
import { ErrorState, Skeleton } from '@/components/ui/Feedback';
import { NecklaceHero } from '@/features/necklace/NecklaceHero';
import { env } from '@/lib/env';

function SectionHeading({
  eyebrow,
  title,
  action,
}: {
  eyebrow?: string;
  title: string;
  action?: { to: string; label: string };
}) {
  return (
    <div className="mb-10 flex items-end justify-between gap-6">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 className="mt-2 font-display text-3xl font-medium tracking-tight sm:text-4xl">
          {title}
        </h2>
      </div>
      {action && (
        <Link
          to={action.to}
          className="group hidden shrink-0 items-center gap-2 text-sm font-medium sm:inline-flex"
        >
          {action.label}
          <ArrowRight
            className="size-4 transition-transform group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </Link>
      )}
    </div>
  );
}

/**
 * Opening section: scattered diamonds assemble into a gold necklace as the visitor scrolls (and
 * come apart again on the way back). The copy is ordinary HTML, so it paints first; the 3D scene
 * loads afterwards. With "reduce motion" the finished necklace is shown still.
 */
function Hero() {
  return (
    <NecklaceHero>
      <Container className="flex h-full flex-col justify-start pt-10 sm:pt-14 lg:justify-center lg:pt-0">
        <div data-hero-copy="" className="max-w-xl">
          <p className="text-xs font-medium tracking-(--tracking-eyebrow) text-noir-muted uppercase">
            Fine gold jewellery
          </p>
          <h1 className="mt-4 font-display text-4xl leading-[1.05] font-medium tracking-tight sm:mt-5 sm:text-6xl xl:text-7xl">
            Gold jewellery,
            <br />
            <em className="font-medium text-gold">priced in the open</em>
          </h1>
          <p className="mt-4 max-w-md text-base leading-relaxed text-noir-muted sm:mt-6 sm:text-lg">
            Every piece shows its gold value, making charges and GST separately — so you know
            exactly what you are paying for.
          </p>
          <div className="mt-5 flex flex-wrap gap-3 sm:mt-9">
            {/* Compact on phones so the copy leaves room for the necklace below it. */}
            <Button
              asChild
              size="lg"
              className="min-h-11 bg-noir-ink px-5 text-sm text-noir hover:bg-noir-ink/90 sm:min-h-13 sm:px-8 sm:text-base"
            >
              <Link to="/collections">Shop all jewellery</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="secondary"
              className="min-h-11 border-noir-ink/70 px-5 text-sm text-noir-ink hover:bg-noir-ink hover:text-noir sm:min-h-13 sm:px-8 sm:text-base"
            >
              <Link to="/gold-buying-guide">
                <span className="sm:hidden">Buying guide</span>
                <span className="hidden sm:inline">Read the buying guide</span>
              </Link>
            </Button>
          </div>
        </div>
      </Container>
    </NecklaceHero>
  );
}

function Section({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section className={className}>
      <Container className="py-16 lg:py-24">{children}</Container>
    </section>
  );
}

function ProductSection({
  eyebrow,
  title,
  products,
  action,
}: {
  eyebrow?: string;
  title: string;
  products: ProductCardData[];
  action: { to: string; label: string };
}) {
  if (products.length === 0) return null;
  return (
    <Section>
      <SectionHeading eyebrow={eyebrow} title={title} action={action} />
      <ProductGrid products={products.slice(0, 8)} />
      <div className="mt-10 sm:hidden">
        <Button asChild variant="secondary" className="w-full">
          <Link to={action.to}>{action.label}</Link>
        </Button>
      </div>
    </Section>
  );
}

const PROMISES = [
  {
    icon: Receipt,
    title: 'Itemised pricing',
    text: 'Gold value, making charges, stones and GST are always shown separately.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure checkout',
    text: 'Payments are processed by Razorpay. We never see or store your card details.',
  },
  {
    icon: MapPin,
    title: 'Delivery dates up front',
    text: 'Check your PIN code on any piece to see delivery options before you buy.',
  },
  {
    icon: BookOpen,
    title: 'Honest guidance',
    text: 'Plain-language guides to purity, hallmarks and caring for your gold.',
  },
];

export function HomePage() {
  const home = useHome();

  return (
    <>
      <PageMeta
        title={env.storeName}
        description="Fine gold jewellery with transparent, itemised pricing — rings, earrings, necklaces, bangles and more."
        path="/"
        image="/images/placeholders/hero.svg"
      />
      <Hero />

      {home.isError && <ErrorState error={home.error} onRetry={() => void home.refetch()} />}

      {/* Shop by category */}
      <Section>
        <SectionHeading
          eyebrow="Explore"
          title="Shop by category"
          action={{ to: '/collections', label: 'All jewellery' }}
        />
        <ul className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-4 sm:gap-6 sm:overflow-visible sm:px-0 lg:grid-cols-8">
          {home.isPending
            ? Array.from({ length: 8 }, (_, i) => (
                <li key={i} className="w-32 shrink-0 sm:w-auto">
                  <Skeleton className="aspect-square w-full" />
                  <Skeleton className="mx-auto mt-3 h-4 w-2/3" />
                </li>
              ))
            : home.data?.categories.map((category) => (
                <li key={category.slug} className="w-32 shrink-0 snap-start sm:w-auto">
                  <Link to={`/collections/${category.slug}`} className="group block text-center">
                    <span className="block aspect-square overflow-hidden rounded-sm bg-surface-muted">
                      {category.image_url && (
                        <img
                          src={category.image_url}
                          alt=""
                          loading="lazy"
                          width={800}
                          height={1000}
                          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03] motion-reduce:transition-none"
                        />
                      )}
                    </span>
                    <span className="mt-3 block text-sm font-medium">{category.name}</span>
                  </Link>
                </li>
              ))}
        </ul>
      </Section>

      {home.isPending && (
        <Section>
          <Skeleton className="mb-10 h-10 w-64" />
          <ProductGrid loading skeletonCount={4} />
        </Section>
      )}

      {home.data && (
        <ProductSection
          eyebrow="Just in"
          title="New arrivals"
          products={home.data.new_arrivals}
          action={{ to: '/collections?sort=newest', label: 'View all new arrivals' }}
        />
      )}

      {/* Featured collections */}
      {home.data && home.data.collections.length > 0 && (
        <Section className="bg-surface">
          <SectionHeading eyebrow="Curated" title="Collections" />
          <ul className="grid gap-8 md:grid-cols-3">
            {home.data.collections.map((collection) => (
              <li key={collection.slug}>
                <Link to={`/collections/${collection.slug}`} className="group block">
                  <span className="block aspect-4/5 overflow-hidden rounded-sm bg-surface-muted">
                    {collection.hero_image_url && (
                      <img
                        src={collection.hero_image_url}
                        alt=""
                        loading="lazy"
                        width={800}
                        height={1000}
                        className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.02] motion-reduce:transition-none"
                      />
                    )}
                  </span>
                  <span className="mt-5 block font-display text-2xl">{collection.name}</span>
                  {collection.description && (
                    <span className="mt-1 block text-sm text-ink-muted">
                      {collection.description}
                    </span>
                  )}
                  <span className="mt-3 inline-flex items-center gap-2 text-sm font-medium">
                    Explore the collection
                    <ArrowRight
                      className="size-4 transition-transform group-hover:translate-x-0.5"
                      aria-hidden="true"
                    />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {home.data && (
        <ProductSection
          eyebrow="Most chosen"
          title="Bestsellers"
          products={home.data.bestsellers}
          action={{ to: '/collections', label: 'Shop all jewellery' }}
        />
      )}

      {/* Our approach — the brand story section (owner to personalise in Our story). */}
      <section className="bg-noir text-noir-ink">
        <Container className="grid gap-12 py-20 lg:grid-cols-2 lg:items-center lg:py-28">
          <div>
            <p className="text-xs font-medium tracking-[0.18em] text-gold uppercase">
              Our approach
            </p>
            <h2 className="mt-4 font-display text-4xl leading-tight font-medium sm:text-5xl">
              Fair prices you can read line by line
            </h2>
          </div>
          <div className="space-y-5 text-noir-muted">
            <p>
              Gold jewellery is priced from the day’s gold rate for its purity, plus the cost of
              craftsmanship. We show both — along with any stones and GST — on every piece, so the
              number you see is never a mystery.
            </p>
            <p>
              If a price changes while a piece is in your cart, we tell you and ask before you pay.
            </p>
            <Link
              to="/about"
              className="inline-flex items-center gap-2 text-sm font-medium text-noir-ink underline decoration-gold underline-offset-4"
            >
              Read our story
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </Container>
      </section>

      {home.data && home.data.featured.length > 0 && (
        <ProductSection
          eyebrow="Selected"
          title="Featured pieces"
          products={home.data.featured}
          action={{ to: '/collections', label: 'Shop all jewellery' }}
        />
      )}

      {/* Promises — only statements the system actually guarantees. */}
      <section className="border-y border-line bg-surface">
        <Container className="grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-4">
          {PROMISES.map(({ icon: Icon, title, text }) => (
            <div key={title}>
              <Icon className="size-6 text-gold" strokeWidth={1.25} aria-hidden="true" />
              <h3 className="mt-4 text-sm font-medium">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{text}</p>
            </div>
          ))}
        </Container>
      </section>

      {/* Guides */}
      <Section>
        <SectionHeading eyebrow="Learn" title="Buying and caring for gold" />
        <div className="grid gap-6 md:grid-cols-2">
          {[
            {
              to: '/gold-buying-guide',
              title: 'Gold buying guide',
              text: 'Karats, hallmarks and how a gold price is made up.',
            },
            {
              to: '/jewellery-care',
              title: 'Caring for your jewellery',
              text: 'Simple habits that keep gold bright for years.',
            },
          ].map((guide) => (
            <Link
              key={guide.to}
              to={guide.to}
              className="group flex items-start justify-between gap-6 rounded-md border border-line bg-surface p-8 transition-colors hover:border-ink/40"
            >
              <span>
                <Sparkles className="size-5 text-gold" strokeWidth={1.25} aria-hidden="true" />
                <span className="mt-4 block font-display text-2xl">{guide.title}</span>
                <span className="mt-1 block text-sm text-ink-muted">{guide.text}</span>
              </span>
              <ArrowRight
                className="mt-1 size-5 shrink-0 transition-transform group-hover:translate-x-1"
                aria-hidden="true"
              />
            </Link>
          ))}
        </div>
      </Section>
    </>
  );
}
