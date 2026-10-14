import ReactMarkdown, { type Components } from 'react-markdown';
import { Link } from 'react-router';
import remarkGfm from 'remark-gfm';

import { ApiError } from '@/api/client';
import { useContentPage } from '@/api/queries/catalogue';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { Alert, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { NotFoundPage } from '@/pages/NotFoundPage';

/** Internal links use the router; external links open safely in a new tab. */
const components: Components = {
  a: ({ href = '', children }) =>
    href.startsWith('/') ? (
      <Link to={href}>{children}</Link>
    ) : (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
};

/**
 * Editable content page (about, FAQ, guides, policies). Markdown is rendered WITHOUT raw HTML
 * (react-markdown's default), so admin-entered content cannot inject scripts.
 */
export function ContentPage({ slug, path }: { slug: string; path: string }) {
  const page = useContentPage(slug);

  if (page.isPending) {
    return (
      <Container className="max-w-3xl py-16">
        <Skeleton className="mx-auto h-12 w-2/3" />
        <Skeleton className="mt-10 h-4 w-full" />
        <Skeleton className="mt-3 h-4 w-5/6" />
        <Skeleton className="mt-3 h-4 w-4/6" />
      </Container>
    );
  }
  if (page.isError) {
    if (page.error instanceof ApiError && page.error.status === 404) return <NotFoundPage />;
    return <ErrorState error={page.error} onRetry={() => void page.refetch()} />;
  }

  const data = page.data;
  return (
    <>
      <PageMeta title={data.title} description={data.summary ?? undefined} path={path} />
      <Container className="max-w-3xl pb-20">
        <PageHeader title={data.title} description={data.summary} />
        {data.is_draft_template && (
          <Alert tone="warning" title="Draft content" className="mb-10">
            This page is a template awaiting review by the store owner and is shown for development
            purposes.
          </Alert>
        )}
        <div className="prose-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
            {data.body_markdown}
          </ReactMarkdown>
        </div>
      </Container>
    </>
  );
}
