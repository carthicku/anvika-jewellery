/**
 * Full-height hero whose background is the scroll-assembled 3D necklace.
 *
 * This file is in the main bundle and holds only the frame and the copy (so the headline paints
 * immediately and is the LCP element). The 3D scene and its scroll control are loaded afterwards
 * from ./NecklaceStage, in their own chunk, but only once the page has finished loading and the
 * browser is idle: on slow connections that chunk (≈290 kB) must not compete with the headline's
 * font and the page's own requests. Until then — or without WebGL — the section is simply the dark
 * hero with its text.
 */
import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react';

import { cn } from '@/lib/cn';

import type { NecklaceStageProps, StageMode } from './NecklaceStage';

const NecklaceStage = lazy(() => import('./NecklaceStage'));

export type { StageMode };

/** True once the page has loaded and the browser has a quiet moment (or after a short timeout). */
function useAfterLoad(): boolean {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let cancelled = false;
    let idle: number | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const go = () => {
      if (!cancelled) setReady(true);
    };
    const schedule = () => {
      if ('requestIdleCallback' in window) idle = window.requestIdleCallback(go, { timeout: 1500 });
      else timer = setTimeout(go, 200);
    };
    if (document.readyState === 'complete') schedule();
    else window.addEventListener('load', schedule, { once: true });
    return () => {
      cancelled = true;
      window.removeEventListener('load', schedule);
      if (idle !== undefined) window.cancelIdleCallback(idle);
      if (timer !== undefined) clearTimeout(timer);
    };
  }, []);
  return ready;
}

export function NecklaceHero({
  children,
  className,
  onProgress,
  onModeChange,
}: {
  children: ReactNode;
  className?: string;
} & Pick<NecklaceStageProps, 'onProgress' | 'onModeChange'>) {
  const section = useRef<HTMLElement>(null);
  const loadStage = useAfterLoad();
  return (
    <section
      ref={section}
      data-necklace-hero=""
      data-progress="0.000"
      className={cn(
        // One screen tall below the sticky header (--header-h is measured by RootLayout).
        'relative isolate h-[calc(100svh-var(--header-h,4rem))] min-h-[34rem] overflow-hidden bg-noir text-noir-ink',
        className,
      )}
    >
      {/* Decorative: the canvas has no information that isn't in the text. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
        {loadStage && (
          <Suspense fallback={null}>
            <NecklaceStage
              triggerRef={section}
              onProgress={onProgress}
              onModeChange={onModeChange}
            />
          </Suspense>
        )}
      </div>
      {children}
    </section>
  );
}
