import type { Image } from '@/api/types';

/**
 * Product image with responsive renditions when available (uploaded photos) and lazy loading
 * below the fold. Width/height prevent layout shift.
 */
export function ProductImage({
  image,
  sizes,
  priority = false,
  className,
}: {
  image: Image;
  sizes: string;
  priority?: boolean;
  className?: string;
}) {
  const renditions = Object.entries(image.renditions);
  const srcSet = renditions.length
    ? renditions.map(([width, url]) => `${url} ${width}w`).join(', ')
    : undefined;
  return (
    <img
      src={image.url}
      srcSet={srcSet}
      sizes={srcSet ? sizes : undefined}
      alt={image.alt}
      width={image.width ?? 800}
      height={image.height ?? 1000}
      loading={priority ? 'eager' : 'lazy'}
      fetchPriority={priority ? 'high' : undefined}
      decoding="async"
      className={className}
    />
  );
}
