/**
 * The 3D necklace and its scroll control. Loaded lazily (three.js + R3F + GSAP stay out of the
 * initial bundle). See ./timeline.ts for the animation itself.
 *
 * Scroll → progress: one GSAP tween on a plain `{ p }` object, scrubbed by ScrollTrigger while the
 * hero is pinned. Progress → picture: `computeFrame(p)` on every rendered frame. Because the scene
 * depends only on `p`, scrolling backwards disassembles the necklace along the identical path, and
 * resizing or jumping (Home/End keys, scrollbar drags) never needs a reset or a replay.
 *
 * Rendering is on demand: a frame is drawn only when progress or the canvas size changes.
 * With "reduce motion" there is no pin and no scrub: the finished necklace is shown as a still.
 */
import { useGSAP } from '@gsap/react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useLayoutEffect, useMemo, useRef, useState, type RefObject } from 'react';
import { type Group, type InstancedMesh, LatheGeometry, TorusGeometry, Vector2 } from 'three';

import { createDiamondMaterial, createGoldMaterial } from './materials';
import { computeFrame, createFrame, createLayout } from './timeline';

gsap.registerPlugin(ScrollTrigger, useGSAP);
// Mobile address bars showing/hiding must not re-measure (and jump) the pinned section.
ScrollTrigger.config({ ignoreMobileResize: true });

/** Scroll distance of the pinned animation, in viewport heights. */
export const PIN_SCREENS = 1.6;

export type StageMode = 'scroll' | 'static' | 'unsupported';

export interface NecklaceStageProps {
  /** The hero <section>: pinned while the necklace assembles; receives data-progress. */
  triggerRef: RefObject<HTMLElement | null>;
  onProgress?: (p: number) => void;
  onModeChange?: (mode: StageMode) => void;
}

function hasWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

/**
 * Where the hero copy (marked `data-hero-copy`) ends, as a fraction of the hero's height, kept up
 * to date as fonts load, text wraps or the window changes size.
 */
function useCopyBottom(triggerRef: RefObject<HTMLElement | null>): number {
  const [bottom, setBottom] = useState(0.5);
  useLayoutEffect(() => {
    const section = triggerRef.current;
    const copy = section?.querySelector<HTMLElement>('[data-hero-copy]');
    if (!section || !copy || typeof ResizeObserver === 'undefined') return;
    const measure = () => {
      const box = section.getBoundingClientRect();
      const text = copy.getBoundingClientRect();
      if (box.height > 0) setBottom(Math.min(1, Math.max(0, (text.bottom - box.top) / box.height)));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(section);
    observer.observe(copy);
    return () => {
      observer.disconnect();
    };
  }, [triggerRef]);
  return bottom;
}

/** Height of the sticky site header, so the pinned hero sits just below it. */
function headerHeight(): number {
  return document.querySelector<HTMLElement>('body > #root header')?.offsetHeight ?? 0;
}

// Extent of the finished necklace in world units (chain ends at the top, pendant at the bottom).
const PIECE_WIDTH = 3.3;
const PIECE_TOP = 1.8;
const PIECE_BOTTOM = -1.85; // pendant + perspective margin

/**
 * Frames the piece for the canvas shape. Wide screens: the copy is on the left, so the necklace
 * sits in the right half. Narrow screens: the copy is on top, so the necklace is fitted into the
 * free space below it (`freeTop` = where the copy ends, as a fraction of the hero's height).
 */
function useFraming(group: RefObject<Group | null>, freeTop: number) {
  const camera = useThree((s) => s.camera);
  const size = useThree((s) => s.size);
  const invalidate = useThree((s) => s.invalidate);
  useLayoutEffect(() => {
    const aspect = size.width / Math.max(1, size.height);
    const halfFov = Math.tan(((35 / 2) * Math.PI) / 180);
    const pieceHeight = PIECE_TOP - PIECE_BOTTOM;
    const pieceCentre = (PIECE_TOP + PIECE_BOTTOM) / 2;
    if (aspect >= 1.05) {
      const distance = Math.max(7.2, 3.6 / (halfFov * aspect));
      camera.position.set(0, 0, distance);
      const halfWidth = halfFov * distance * aspect;
      group.current?.position.set(halfWidth * 0.42, 0, 0);
    } else {
      // Free band below the copy, with a small margin; never less than 40% of the hero.
      const top = Math.min(0.6, freeTop + 0.03);
      const band = Math.max(0.4, 0.97 - top);
      const fitHeight = pieceHeight / (2 * band * halfFov);
      const fitWidth = PIECE_WIDTH / (2 * 0.88 * halfFov * aspect);
      const distance = Math.max(8, fitHeight, fitWidth);
      camera.position.set(0, 0, distance);
      const halfHeight = halfFov * distance;
      const bandCentre = top + band / 2; // from the top, 0…1
      group.current?.position.set(0, halfHeight * (1 - 2 * bandCentre) - pieceCentre, 0);
    }
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, size, group, invalidate, freeTop]);
}

function Necklace({ progress, freeTop }: { progress: RefObject<number>; freeTop: number }) {
  const layout = useMemo(() => createLayout(), []);
  const frame = useMemo(() => createFrame(layout), [layout]);
  const group = useRef<Group>(null);
  const stones = useRef<InstancedMesh>(null);
  const settings = useRef<InstancedMesh>(null);
  const links = useRef<InstancedMesh>(null);
  const drawn = useRef(Number.NaN);
  useFraming(group, freeTop);

  // Brilliant-cut silhouette (pavilion → girdle → crown → table), faceted by flat shading.
  const stoneGeometry = useMemo(
    () =>
      new LatheGeometry(
        [
          new Vector2(0.001, -0.62),
          new Vector2(1, 0),
          new Vector2(1, 0.05),
          new Vector2(0.44, 0.36),
          new Vector2(0.001, 0.36),
        ],
        16,
      ),
    [],
  );
  const settingGeometry = useMemo(() => new TorusGeometry(1, 0.12, 8, 32), []);
  const linkGeometry = useMemo(() => {
    const torus = new TorusGeometry(0.034, 0.009, 6, 20);
    torus.scale(1.45, 1, 1); // oval links
    return torus;
  }, []);
  // Matcaps: lighting baked into a small texture (cheap on phones; see ./materials.ts).
  const diamond = useMemo(() => createDiamondMaterial(), []);
  const gold = useMemo(() => createGoldMaterial(), []);

  useLayoutEffect(
    () => () => {
      stoneGeometry.dispose();
      settingGeometry.dispose();
      linkGeometry.dispose();
      diamond.matcap?.dispose();
      diamond.dispose();
      gold.matcap?.dispose();
      gold.dispose();
    },
    [stoneGeometry, settingGeometry, linkGeometry, diamond, gold],
  );

  useFrame(() => {
    const p = progress.current;
    if (p === drawn.current) return;
    drawn.current = p;
    computeFrame(p, layout, frame);
    for (const [mesh, data] of [
      [stones.current, frame.stones],
      [settings.current, frame.settings],
      [links.current, frame.links],
    ] as const) {
      if (!mesh) continue;
      (mesh.instanceMatrix.array as Float32Array).set(data);
      mesh.instanceMatrix.needsUpdate = true;
    }
    if (group.current) group.current.rotation.y = frame.turn;
  });

  return (
    <group ref={group}>
      <group rotation={[0.12, 0, 0]}>
        <instancedMesh
          ref={stones}
          args={[stoneGeometry, diamond, layout.stones.length]}
          frustumCulled={false}
        />
        <instancedMesh
          ref={settings}
          args={[settingGeometry, gold, layout.stones.length]}
          frustumCulled={false}
        />
        <instancedMesh
          ref={links}
          args={[linkGeometry, gold, layout.links.length]}
          frustumCulled={false}
        />
      </group>
    </group>
  );
}

declare global {
  interface Window {
    /** E2E only: keep the WebGL drawing buffer so tests can compare rendered pixels. */
    __NECKLACE_CAPTURE__?: boolean;
  }
}

export default function NecklaceStage({
  triggerRef,
  onProgress,
  onModeChange,
}: NecklaceStageProps) {
  const [supported] = useState(hasWebGL);
  const progress = useRef(0);
  const freeTop = useCopyBottom(triggerRef);
  const invalidate = useRef<() => void>(() => undefined);

  const report = (p: number) => {
    progress.current = p;
    const section = triggerRef.current;
    if (section) section.dataset.progress = p.toFixed(3);
    invalidate.current();
    onProgress?.(p);
  };

  useGSAP(
    () => {
      const section = triggerRef.current;
      if (!section) return;
      if (!supported) {
        section.dataset.necklaceMode = 'unsupported';
        onModeChange?.('unsupported');
        return;
      }
      const mm = gsap.matchMedia();
      mm.add(
        {
          motion: '(prefers-reduced-motion: no-preference)',
          reduce: '(prefers-reduced-motion: reduce)',
        },
        (context) => {
          if (context.conditions?.reduce) {
            // No pinning, no scrubbing: a still of the finished piece.
            section.dataset.necklaceMode = 'static';
            onModeChange?.('static');
            report(1);
            return;
          }
          section.dataset.necklaceMode = 'scroll';
          onModeChange?.('scroll');
          const state = { p: 0 };
          gsap.fromTo(
            state,
            { p: 0 },
            {
              p: 1,
              ease: 'none',
              onUpdate: () => {
                report(state.p);
              },
              scrollTrigger: {
                trigger: section,
                start: () => `top top+=${String(headerHeight())}`,
                end: () => `+=${String(Math.round(window.innerHeight * PIN_SCREENS))}`,
                pin: true,
                scrub: 0.6, // smooths wheel steps; still converges to exactly the scroll position
                invalidateOnRefresh: true,
                anticipatePin: 1,
              },
            },
          );
          report(state.p);
        },
      );
      return () => {
        mm.revert();
      };
    },
    { dependencies: [supported], revertOnUpdate: true },
  );

  if (!supported) return null;
  return (
    <Canvas
      className="!absolute inset-0"
      frameloop="demand"
      dpr={[1, 1.5]}
      camera={{ fov: 35, near: 0.1, far: 100, position: [0, 0, 8] }}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
        preserveDrawingBuffer: window.__NECKLACE_CAPTURE__ === true,
      }}
      onCreated={(state) => {
        invalidate.current = () => {
          state.invalidate();
        };
        state.invalidate();
      }}
    >
      <Necklace progress={progress} freeTop={freeTop} />
    </Canvas>
  );
}
