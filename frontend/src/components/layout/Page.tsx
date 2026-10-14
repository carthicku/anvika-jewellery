import { ChevronRight } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { cn } from '@/lib/cn';
import { env } from '@/lib/env';

export function Container({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn('mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8', className)}>{children}</div>
  );
}

export interface Crumb {
  label: string;
  to?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-1 text-xs text-ink-muted">
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`} className="flex items-center gap-1">
            {index > 0 && <ChevronRight className="size-3 text-ink-subtle" aria-hidden="true" />}
            {item.to && index < items.length - 1 ? (
              <Link to={item.to} className="hover:text-ink hover:underline">
                {item.label}
              </Link>
            ) : (
              <span aria-current={index === items.length - 1 ? 'page' : undefined}>
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** Eyebrow + H1 + description, used at the top of listing and content pages. */
export function PageHeader({
  eyebrow,
  title,
  description,
  crumbs,
  align = 'center',
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  crumbs?: Crumb[];
  align?: 'center' | 'left';
  children?: ReactNode;
}) {
  return (
    <header className={cn('pt-8 pb-10 sm:pt-12 sm:pb-14', align === 'center' && 'text-center')}>
      {crumbs && (
        <div className={cn('mb-6 flex', align === 'center' && 'justify-center')}>
          <Breadcrumbs items={crumbs} />
        </div>
      )}
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1 className="mt-3 font-display text-4xl font-medium tracking-tight text-balance sm:text-5xl">
        {title}
      </h1>
      {description && (
        <div className={cn('mt-4 max-w-2xl text-ink-muted', align === 'center' && 'mx-auto')}>
          {description}
        </div>
      )}
      {children}
    </header>
  );
}

/** Per-page metadata. React 19 hoists these elements into <head>. */
export function PageMeta({
  title,
  description,
  path,
  noindex = false,
  image,
}: {
  title: string;
  description?: string;
  path?: string;
  noindex?: boolean;
  image?: string;
}) {
  const fullTitle = title === env.storeName ? title : `${title} — ${env.storeName}`;
  const canonical = path ? `${env.siteUrl}${path}` : undefined;
  return (
    <>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      {canonical && <link rel="canonical" href={canonical} />}
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      {canonical && <meta property="og:url" content={canonical} />}
      {image && (
        <meta
          property="og:image"
          content={image.startsWith('http') ? image : `${env.siteUrl}${image}`}
        />
      )}
      <meta property="og:site_name" content={env.storeName} />
    </>
  );
}
