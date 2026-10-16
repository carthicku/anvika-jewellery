/**
 * Matcap ("material capture") textures for the necklace, painted on a small 2D canvas at start-up.
 *
 * A matcap bakes lighting and reflections into one image that the shader looks up by surface
 * direction. That gives polished gold and bright faceted stones with a tiny shader, no lights and
 * no environment map — far cheaper to compile and draw than physically based materials, which
 * matters on phones. 3D colours can't use the CSS tokens directly; the gold is tuned so that it
 * reads as the brand gold (--color-gold #b08d57) on the noir hero.
 */
import { CanvasTexture, MeshMatcapMaterial, SRGBColorSpace } from 'three';

type Stop = [offset: number, colour: string];

function paint(
  size: number,
  layers: { centre: [number, number]; radius: number; stops: Stop[] }[],
) {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('2D canvas unavailable');
  for (const layer of layers) {
    const [x, y] = layer.centre;
    const gradient = context.createRadialGradient(
      x * size,
      y * size,
      0,
      x * size,
      y * size,
      layer.radius * size,
    );
    for (const [offset, colour] of layer.stops) gradient.addColorStop(offset, colour);
    context.fillStyle = gradient;
    context.fillRect(0, 0, size, size);
  }
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/** Warm polished gold: deep edges, rich body, a soft highlight from the upper left. */
export function createGoldMaterial() {
  const texture = paint(256, [
    {
      centre: [0.5, 0.5],
      radius: 0.5,
      stops: [
        [0, '#e9c98a'],
        [0.45, '#c79a52'],
        [0.8, '#8a6428'],
        [1, '#3c2a10'],
      ],
    },
    {
      centre: [0.36, 0.32],
      radius: 0.22,
      stops: [
        [0, 'rgba(255, 246, 222, 0.95)'],
        [1, 'rgba(255, 246, 222, 0)'],
      ],
    },
  ]);
  return new MeshMatcapMaterial({ matcap: texture });
}

/**
 * Faceted stone: strong light/dark banding so neighbouring facets (flat shading) catch different
 * values and the stone sparkles as it turns.
 */
export function createDiamondMaterial() {
  const texture = paint(256, [
    {
      centre: [0.5, 0.5],
      radius: 0.5,
      stops: [
        [0, '#dfe6ee'],
        [0.12, '#ffffff'],
        [0.22, '#c3ccd8'],
        [0.38, '#7d8796'],
        [0.52, '#f7f9fc'],
        [0.68, '#a7b1bf'],
        [0.84, '#ffffff'],
        [1, '#5d6673'],
      ],
    },
    {
      centre: [0.3, 0.28],
      radius: 0.16,
      stops: [
        [0, 'rgba(255, 255, 255, 1)'],
        [1, 'rgba(255, 255, 255, 0)'],
      ],
    },
  ]);
  return new MeshMatcapMaterial({ matcap: texture, flatShading: true });
}
