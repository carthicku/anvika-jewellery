/**
 * DEVELOPMENT-ONLY prototype page for the scroll-assembled necklace hero (/lab/necklace). It is
 * not registered in production builds. It shows the live scroll progress and mode so forward and
 * backward scrolling, resizing and reduced motion can be checked by hand and by Playwright.
 */
import { useState } from 'react';

import { Container, PageMeta } from '@/components/layout/Page';
import { NecklaceHero, type StageMode } from '@/features/necklace/NecklaceHero';

export function NecklaceLabPage() {
  const [progress, setProgress] = useState(0);
  const [mode, setMode] = useState<StageMode | 'loading'>('loading');
  return (
    <>
      <PageMeta title="Necklace hero prototype" path="/lab/necklace" noindex />
      <NecklaceHero onProgress={setProgress} onModeChange={setMode}>
        <Container className="flex h-full flex-col justify-start pt-10 lg:justify-center lg:pt-0">
          <div data-hero-copy="">
            <p className="text-xs font-medium tracking-(--tracking-eyebrow) text-noir-muted uppercase">
              Prototype
            </p>
            <h1 className="mt-4 max-w-md font-display text-4xl leading-[1.05] font-medium sm:text-5xl">
              Scroll to assemble the necklace
            </h1>
            <p className="mt-4 max-w-sm text-noir-muted">
              Scroll down to set the diamonds; scroll up to take the piece apart again.
            </p>
          </div>
        </Container>
      </NecklaceHero>
      <output
        aria-live="off"
        data-testid="necklace-readout"
        className="fixed right-4 bottom-4 z-40 rounded-sm bg-ink px-3 py-2 font-mono text-xs text-ivory tabular-nums"
      >
        {mode} · {(progress * 100).toFixed(1)}%
      </output>
      <Container className="space-y-6 py-24">
        <h2 className="font-display text-3xl">After the hero</h2>
        {Array.from({ length: 6 }, (_, i) => (
          <p key={i} className="max-w-2xl text-ink-muted">
            Filler content so the page can scroll well past the pinned section and back. Paragraph{' '}
            {i + 1}.
          </p>
        ))}
        <div className="h-[120vh]" />
      </Container>
    </>
  );
}
