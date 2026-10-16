import { Link } from 'react-router';

import { useCategories, usePublicSettings } from '@/api/queries/catalogue';
import { Logo } from '@/components/brand/Logo';
import { env } from '@/lib/env';

import { NewsletterForm } from './NewsletterForm';
import { Container } from './Page';

const HELP = [
  { to: '/contact', label: 'Contact us' },
  { to: '/faq', label: 'FAQ' },
  { to: '/shipping-policy', label: 'Shipping' },
  { to: '/returns-and-exchanges', label: 'Returns & exchanges' },
  { to: '/refund-policy', label: 'Refunds' },
];
const ABOUT = [
  { to: '/about', label: 'Our story' },
  { to: '/gold-buying-guide', label: 'Gold buying guide' },
  { to: '/jewellery-care', label: 'Jewellery care' },
];
const LEGAL = [
  { to: '/privacy-policy', label: 'Privacy policy' },
  { to: '/terms-and-conditions', label: 'Terms & conditions' },
];

function Column({ title, links }: { title: string; links: { to: string; label: string }[] }) {
  return (
    <div>
      <h2 className="text-xs font-medium tracking-[0.18em] text-noir-ink uppercase">{title}</h2>
      <ul className="mt-4 space-y-1">
        {links.map((link) => (
          <li key={link.to}>
            <Link
              to={link.to}
              className="inline-flex min-h-9 items-center text-sm text-noir-muted transition-colors hover:text-noir-ink"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SiteFooter() {
  const categories = useCategories();
  const settings = usePublicSettings();
  const shop = (categories.data ?? [])
    .filter((c) => !c.parent_slug)
    .map((c) => ({ to: `/collections/${c.slug}`, label: c.name }));
  const s = settings.data;

  return (
    <footer className="bg-noir text-noir-ink">
      <Container className="py-16 lg:py-20">
        <div className="grid gap-12 lg:grid-cols-[1.3fr_2fr]">
          <div className="max-w-sm">
            <p>
              <span className="sr-only">{env.storeName}</span>
              <Logo className="w-56" />
            </p>
            <p className="mt-4 text-sm leading-relaxed text-noir-muted">
              {s?.tagline ?? 'Fine gold jewellery'}. Every price is shown with its gold value,
              making charges and GST.
            </p>
            <div className="mt-8">
              <h2 className="mb-3 text-xs font-medium tracking-[0.18em] uppercase">
                Stay in touch
              </h2>
              <NewsletterForm tone="dark" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-10 sm:grid-cols-4">
            <Column
              title="Shop"
              links={[{ to: '/collections', label: 'All jewellery' }, ...shop]}
            />
            <Column title="Help" links={HELP} />
            <Column title="About" links={ABOUT} />
            <Column title="Legal" links={LEGAL} />
          </div>
        </div>

        <div className="mt-14 grid gap-6 border-t border-noir-muted/25 pt-8 text-sm text-noir-muted sm:grid-cols-3">
          <p>{s?.business_address ?? ''}</p>
          <p>
            {s?.support_email}
            <br />
            {s?.support_phone}
          </p>
          <p className="sm:text-right">
            © {new Date().getFullYear()} {env.storeName}. Payments secured by Razorpay.
          </p>
        </div>
      </Container>
    </footer>
  );
}
