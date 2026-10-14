import { ChevronLeft, ChevronRight, ZoomIn } from 'lucide-react';
import { useState, type KeyboardEvent } from 'react';

import type { Image } from '@/api/types';
import { DialogContent, DialogRoot, DialogTrigger } from '@/components/ui/Dialog';
import { cn } from '@/lib/cn';

import { ProductImage } from './ProductImage';

/**
 * Main image + thumbnails (arrow keys move between thumbnails) + an enlarged view dialog.
 */
export function ProductGallery({ images, name }: { images: Image[]; name: string }) {
  const [index, setIndex] = useState(0);
  const current = images[index];
  const count = images.length;

  const go = (next: number) => {
    setIndex(((next % count) + count) % count);
  };

  const onThumbKeys = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      go(index + 1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      go(index - 1);
    }
  };

  if (!current) {
    return <div className="aspect-4/5 rounded-sm bg-surface-muted" aria-hidden="true" />;
  }

  return (
    <div className="flex flex-col-reverse gap-4 lg:flex-row">
      {count > 1 && (
        <div
          role="tablist"
          aria-label={`${name} images`}
          aria-orientation="vertical"
          className="flex gap-3 lg:w-20 lg:flex-col"
        >
          {images.map((image, i) => (
            <button
              key={image.url}
              type="button"
              role="tab"
              aria-selected={i === index}
              aria-label={`Show image ${i + 1} of ${count}`}
              tabIndex={i === index ? 0 : -1}
              onKeyDown={onThumbKeys}
              onClick={() => {
                setIndex(i);
              }}
              className={cn(
                'aspect-4/5 w-16 overflow-hidden rounded-sm border bg-surface-muted transition-colors lg:w-full',
                i === index ? 'border-ink' : 'border-transparent hover:border-line-strong',
              )}
            >
              <img src={image.url} alt="" className="h-full w-full object-cover" loading="lazy" />
            </button>
          ))}
        </div>
      )}

      <div className="relative flex-1">
        <DialogRoot>
          <DialogTrigger asChild>
            <button
              type="button"
              className="group relative block w-full cursor-zoom-in overflow-hidden rounded-sm bg-surface-muted"
              aria-label={`Enlarge image: ${current.alt}`}
            >
              <ProductImage
                image={current}
                priority
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="aspect-4/5 h-full w-full object-cover"
              />
              <span className="absolute right-3 bottom-3 inline-flex size-10 items-center justify-center rounded-full bg-surface/85 text-ink opacity-80 transition-opacity group-hover:opacity-100">
                <ZoomIn className="size-4" aria-hidden="true" />
              </span>
            </button>
          </DialogTrigger>
          <DialogContent title={name} hideTitle className="max-w-4xl p-2 sm:p-4">
            <ProductImage
              image={current}
              sizes="90vw"
              className="max-h-[80dvh] w-full rounded-sm object-contain"
            />
            <p className="mt-2 text-center text-xs text-ink-muted">{current.alt}</p>
          </DialogContent>
        </DialogRoot>

        {count > 1 && (
          <div className="absolute inset-x-3 top-1/2 flex -translate-y-1/2 justify-between lg:hidden">
            <button
              type="button"
              onClick={() => {
                go(index - 1);
              }}
              className="inline-flex size-11 items-center justify-center rounded-full bg-surface/85"
              aria-label="Previous image"
            >
              <ChevronLeft className="size-5" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => {
                go(index + 1);
              }}
              className="inline-flex size-11 items-center justify-center rounded-full bg-surface/85"
              aria-label="Next image"
            >
              <ChevronRight className="size-5" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
