import { X } from 'lucide-react';
import { Dialog as D } from 'radix-ui';
import { useRef, type ReactNode } from 'react';

import { cn } from '@/lib/cn';

export const DialogRoot = D.Root;
export const DialogTrigger = D.Trigger;
export const DialogClose = D.Close;

interface ContentProps {
  title: string;
  /** Visually hide the title (it is still announced). */
  hideTitle?: boolean;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
}

const overlay = 'fixed inset-0 z-40 bg-noir/40';

/**
 * Return focus to whatever opened the dialog, even when it was opened from a plain button rather
 * than a Radix <Trigger> (Radix alone would drop focus on <body> in that case).
 */
function useReturnFocus() {
  const opener = useRef<HTMLElement | null>(null);
  return {
    onOpenAutoFocus: () => {
      opener.current =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
    },
    onCloseAutoFocus: (event: Event) => {
      if (opener.current?.isConnected) {
        event.preventDefault();
        opener.current.focus();
      }
    },
  };
}

function CloseButton() {
  return (
    <D.Close
      className="absolute top-3 right-3 inline-flex size-11 items-center justify-center rounded-sm text-ink hover:bg-surface-muted"
      aria-label="Close"
    >
      <X className="size-5" aria-hidden="true" />
    </D.Close>
  );
}

/** Centred modal dialog: traps focus, closes on Esc, returns focus to the trigger. */
export function DialogContent({
  title,
  hideTitle,
  description,
  children,
  className,
}: ContentProps) {
  const returnFocus = useReturnFocus();
  return (
    <D.Portal>
      <D.Overlay className={overlay} />
      <D.Content
        {...returnFocus}
        className={cn(
          'fixed top-1/2 left-1/2 z-50 max-h-[90dvh] w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-md bg-surface p-6 shadow-lift sm:p-8',
          className,
        )}
      >
        <D.Title className={cn('pr-10 font-display text-2xl font-medium', hideTitle && 'sr-only')}>
          {title}
        </D.Title>
        {description ? (
          <D.Description className="mt-2 text-sm text-ink-muted">{description}</D.Description>
        ) : (
          <D.Description className="sr-only">{title}</D.Description>
        )}
        <div className={cn(!hideTitle && 'mt-5')}>{children}</div>
        <CloseButton />
      </D.Content>
    </D.Portal>
  );
}

/** Side drawer (mobile menu, filters). */
export function SheetContent({
  title,
  side = 'left',
  children,
  className,
}: ContentProps & { side?: 'left' | 'right' }) {
  const returnFocus = useReturnFocus();
  return (
    <D.Portal>
      <D.Overlay className={overlay} />
      <D.Content
        {...returnFocus}
        className={cn(
          'fixed inset-y-0 z-50 flex w-[min(24rem,88vw)] flex-col bg-ivory shadow-lift',
          side === 'left' ? 'left-0' : 'right-0',
          className,
        )}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <D.Title className="text-sm font-medium tracking-(--tracking-eyebrow) uppercase">
            {title}
          </D.Title>
          <D.Description className="sr-only">{title}</D.Description>
          <D.Close
            className="-mr-2 inline-flex size-11 items-center justify-center rounded-sm hover:bg-surface-muted"
            aria-label="Close"
          >
            <X className="size-5" aria-hidden="true" />
          </D.Close>
        </div>
        <div className="flex-1 overflow-y-auto pb-[env(safe-area-inset-bottom)]">{children}</div>
      </D.Content>
    </D.Portal>
  );
}
