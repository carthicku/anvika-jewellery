import { Matrix4, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';

import { computeFrame, createFrame, createLayout, STONE_COUNT } from './timeline';

const layout = createLayout();

function frameAt(p: number) {
  return computeFrame(p, layout, createFrame(layout));
}

function decompose(array: Float32Array, index: number) {
  const matrix = new Matrix4().fromArray(array, index * 16);
  // Scale from the basis-vector lengths (decompose() reports 1 for a zero-scale matrix).
  const scale = new Vector3().setFromMatrixColumn(matrix, 0).length();
  return { position: new Vector3().setFromMatrixPosition(matrix), scale: { x: scale } };
}

const visibleLinks = (p: number) => {
  const frame = frameAt(p);
  let count = 0;
  for (let j = 0; j < layout.links.length; j++) {
    if (decompose(frame.links, j).scale.x > 0) count++;
  }
  return count;
};

describe('necklace timeline', () => {
  it('starts with scattered diamonds and no gold', () => {
    const frame = frameAt(0);
    layout.stones.forEach((stone, i) => {
      expect(decompose(frame.stones, i).position.distanceTo(stone.scatter)).toBeLessThan(1e-5);
      expect(decompose(frame.settings, i).scale.x).toBe(0);
    });
    expect(visibleLinks(0)).toBe(0);
  });

  it('ends with every diamond set in a complete gold necklace', () => {
    const frame = frameAt(1);
    expect(layout.stones).toHaveLength(STONE_COUNT);
    layout.stones.forEach((stone, i) => {
      expect(decompose(frame.stones, i).position.distanceTo(stone.target)).toBeLessThan(1e-5);
      expect(decompose(frame.settings, i).scale.x).toBeGreaterThan(0);
    });
    expect(visibleLinks(1)).toBe(layout.links.length);
    expect(layout.links.length).toBeGreaterThan(60);
    expect(frame.turn).toBeCloseTo(0);
  });

  it('is a pure function of progress, so reversing replays the same frames exactly', () => {
    const shared = createFrame(layout);
    const forward: Float32Array[] = [];
    const steps = Array.from({ length: 41 }, (_, i) => i / 40);
    for (const p of steps) forward.push(computeFrame(p, layout, shared).stones.slice());
    // Scroll back down from 100% to 0% with the same (reused) buffers.
    for (const [i, p] of [...steps].reverse().entries()) {
      const back = computeFrame(p, layout, shared).stones;
      expect(Array.from(back)).toEqual(Array.from(forward[steps.length - 1 - i] ?? []));
    }
    // A fresh layout gives identical positions too (seeded, not random per load).
    expect(Array.from(frameAt(0.37).links)).toEqual(
      Array.from(computeFrame(0.37, createLayout(), createFrame(createLayout())).links),
    );
  });

  it('clamps progress outside 0…1 (overscroll, rubber-banding)', () => {
    expect(Array.from(frameAt(-0.5).stones)).toEqual(Array.from(frameAt(0).stones));
    expect(Array.from(frameAt(1.4).links)).toEqual(Array.from(frameAt(1).links));
  });

  it('builds the chain progressively and never removes links while scrolling forward', () => {
    let previous = 0;
    for (let p = 0; p <= 1.0001; p += 0.01) {
      const now = visibleLinks(p);
      expect(now).toBeGreaterThanOrEqual(previous);
      previous = now;
    }
    expect(visibleLinks(0.6)).toBeGreaterThan(0);
    expect(visibleLinks(0.6)).toBeLessThan(layout.links.length);
  });

  it('moves diamonds along curved 3D paths, not straight lines', () => {
    const stone = layout.stones[0];
    if (!stone) throw new Error('no stones');
    const i = 0;
    // Find the halfway point of this stone's journey and compare with the straight-line midpoint.
    const mid = decompose(frameAt(stone.start + 0.21).stones, i).position;
    const straight = stone.scatter.clone().lerp(stone.target, 0.5);
    expect(mid.distanceTo(straight)).toBeGreaterThan(0.3);
    expect(mid.z).not.toBeCloseTo(straight.z, 1); // it travels in depth as well
  });
});
