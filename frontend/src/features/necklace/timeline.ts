/**
 * The necklace hero's animation as a PURE function of scroll progress `p` (0 → 1).
 *
 * p = 0: diamonds scattered in space. As p grows, each diamond flies along its own curved 3D path
 * (a quadratic Bézier) to its place on the necklace, then gold settings grow around the stones and
 * chain links appear from the centre out to the clasp. Nothing here remembers previous frames:
 * the same `p` always produces exactly the same scene, so scrolling back plays the identical
 * timeline in reverse, and jumping to any point (resize, reload, fast scroll) needs no replay.
 *
 * Everything is decorative; there are no business facts here.
 */
import { Euler, Matrix4, Quaternion, Vector3 } from 'three';

// ---------------------------------------------------------------------------------- tuning

/** Diamonds along the front of the necklace (odd, so one sits in the centre as a pendant). */
export const STONE_COUNT = 21;
/** Gap between chain link centres (world units). */
const LINK_PITCH = 0.082;

// Necklace curve: the lower part of an ellipse, seen from the front, with a little depth.
const CURVE_A = 1.5; // half-width
const CURVE_B = 1.42; // drop
const CURVE_Y0 = 0.42; // vertical offset so the whole piece is centred
const CURVE_DEPTH = 0.32; // the bottom of the necklace comes towards the viewer
const PHI_MAX = 0.86 * Math.PI; // chain ends (towards the clasp)
const STONE_SPAN = 0.5 * Math.PI; // stones sit on the front half
const PENDANT_DROP = 0.34;

// Phases of the timeline (fractions of p). Each element runs inside its own window.
const STONE_STAGGER = 0.3; // outer stones start first, the centre stone last
const STONE_TRAVEL = 0.42; // → all stones placed by p = 0.72
const SETTING_START = 0.42;
const SETTING_STAGGER = 0.2;
const SETTING_GROW = 0.14; // → all settings complete by p = 0.76
const CHAIN_START = 0.58;
const CHAIN_SPREAD = 0.34; // centre links first, the last link at the clasp by p ≈ 0.97
const LINK_GROW = 0.05;
const BAIL_START = 0.72;

// ---------------------------------------------------------------------------------- helpers

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
/** Local progress of a window [start, start + length] on the timeline. */
export const windowProgress = (p: number, start: number, length: number) =>
  clamp01((p - start) / length);
const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const easeOutCubic = (t: number) => 1 - (1 - t) ** 3;
/** Gentle overshoot for links/settings "snapping" into place (still a pure function of t). */
const easeOutBack = (t: number) => {
  const c = 1.4;
  return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2;
};

/** Small deterministic PRNG so the scattered layout is the same on every load. */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function curvePoint(phi: number, out = new Vector3()): Vector3 {
  return out.set(
    CURVE_A * Math.sin(phi),
    CURVE_Y0 - CURVE_B * Math.cos(phi),
    CURVE_DEPTH * Math.cos(phi),
  );
}

function curveTangent(phi: number, out = new Vector3()): Vector3 {
  return out
    .set(CURVE_A * Math.cos(phi), CURVE_B * Math.sin(phi), -CURVE_DEPTH * Math.sin(phi))
    .normalize();
}

// ---------------------------------------------------------------------------------- layout

export interface Stone {
  /** -1 … 1 along the front of the necklace (0 = centre/pendant). */
  u: number;
  size: number;
  scatter: Vector3;
  control: Vector3;
  target: Vector3;
  startRotation: Quaternion;
  endRotation: Quaternion;
  spin: number;
  start: number;
}

export interface Link {
  position: Vector3;
  rotation: Quaternion;
  start: number;
  scale: number;
}

export interface Layout {
  stones: Stone[];
  /** Chain links, plus the pendant's bail as the last entry. */
  links: Link[];
}

/** The stone's final orientation: table (lathe +Y) turned to face the viewer (+Z), tipped slightly down. */
const FACING = new Quaternion().setFromEuler(new Euler(Math.PI / 2 - 0.28, 0, 0));
/** Torus geometry lies in the XY plane; rotate so its ring wraps the stone's girdle. */
const RING_TO_GIRDLE = new Quaternion().setFromEuler(new Euler(Math.PI / 2, 0, 0));

/** Arc-length table so chain links are evenly spaced along the curve. */
function arcLengthTable(samples = 1024) {
  const phis: number[] = [];
  const lengths: number[] = [0];
  const a = new Vector3();
  const b = new Vector3();
  for (let i = 0; i <= samples; i++) {
    const phi = -PHI_MAX + (2 * PHI_MAX * i) / samples;
    phis.push(phi);
    if (i > 0) {
      curvePoint(phis[i - 1] ?? phi, a);
      curvePoint(phi, b);
      lengths.push((lengths[i - 1] ?? 0) + a.distanceTo(b));
    }
  }
  return { phis, lengths, total: lengths[lengths.length - 1] ?? 0 };
}

function phiAtLength(table: ReturnType<typeof arcLengthTable>, length: number): number {
  const { phis, lengths } = table;
  let lo = 0;
  let hi = lengths.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if ((lengths[mid] ?? 0) < length) lo = mid;
    else hi = mid;
  }
  const l0 = lengths[lo] ?? 0;
  const l1 = lengths[hi] ?? l0;
  const t = l1 > l0 ? (length - l0) / (l1 - l0) : 0;
  return (phis[lo] ?? 0) + ((phis[hi] ?? 0) - (phis[lo] ?? 0)) * t;
}

export function createLayout(seed = 7): Layout {
  const random = mulberry32(seed);
  const between = (min: number, max: number) => min + (max - min) * random();

  const stones: Stone[] = [];
  for (let i = 0; i < STONE_COUNT; i++) {
    const u = (i / (STONE_COUNT - 1)) * 2 - 1;
    const centre = i === (STONE_COUNT - 1) / 2;
    const target = curvePoint(u * STONE_SPAN).add(new Vector3(0, 0, 0.04));
    if (centre) target.y -= PENDANT_DROP;
    const size = centre ? 0.17 : 0.045 + 0.035 * (1 - Math.abs(u)) ** 1.2;
    // Scattered somewhere in a wide, shallow volume around (but mostly beside) the necklace.
    const side = i % 2 === 0 ? -1 : 1;
    const scatter = new Vector3(side * between(1.1, 3.4), between(-2.1, 2.1), between(-2.6, 1.2));
    // Each path bows towards the viewer and swirls sideways, so stones don't travel in a line.
    const control = scatter
      .clone()
      .lerp(target, 0.5)
      .add(new Vector3(between(-1.2, 1.2), between(0.4, 1.4), between(1.0, 2.0)));
    const startRotation = new Quaternion().setFromEuler(
      new Euler(between(0, Math.PI * 2), between(0, Math.PI * 2), between(0, Math.PI * 2)),
    );
    stones.push({
      u,
      size,
      scatter,
      control,
      target,
      startRotation,
      endRotation: FACING.clone(),
      spin: (random() < 0.5 ? -1 : 1) * between(1.5, 3),
      start: STONE_STAGGER * (1 - Math.abs(u)),
    });
  }

  const table = arcLengthTable();
  const count = Math.max(2, Math.round(table.total / LINK_PITCH));
  const links: Link[] = [];
  const tangent = new Vector3();
  const align = new Quaternion();
  const twist = new Quaternion();
  const xAxis = new Vector3(1, 0, 0);
  for (let j = 0; j < count; j++) {
    const length = ((j + 0.5) / count) * table.total;
    const phi = phiAtLength(table, length);
    curveTangent(phi, tangent);
    align.setFromUnitVectors(xAxis, tangent);
    // Cable chain: every other link is turned 90° around the chain's direction.
    twist.setFromAxisAngle(xAxis, j % 2 === 0 ? 0 : Math.PI / 2);
    const fromCentre = Math.abs(length - table.total / 2) / (table.total / 2); // 0 centre → 1 clasp
    links.push({
      position: curvePoint(phi),
      rotation: align.clone().multiply(twist),
      start: CHAIN_START + CHAIN_SPREAD * fromCentre,
      scale: 1,
    });
  }
  // Bail: a vertical link joining the pendant to the chain.
  const pendant = stones[(STONE_COUNT - 1) / 2];
  if (pendant) {
    const top = curvePoint(0);
    links.push({
      position: new Vector3(0, (top.y + pendant.target.y + pendant.size) / 2, top.z + 0.03),
      rotation: new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI / 2),
      start: BAIL_START,
      scale: 1.35,
    });
  }
  return { stones, links };
}

// ---------------------------------------------------------------------------------- frames

export interface Frame {
  /** 16 floats per stone (column-major matrices, ready for an InstancedMesh). */
  stones: Float32Array;
  settings: Float32Array;
  links: Float32Array;
  /** Rotation of the whole piece around the vertical axis. */
  turn: number;
}

export function createFrame(layout: Layout): Frame {
  return {
    stones: new Float32Array(layout.stones.length * 16),
    settings: new Float32Array(layout.stones.length * 16),
    links: new Float32Array(layout.links.length * 16),
    turn: 0,
  };
}

const tmpMatrix = new Matrix4();
const tmpPosition = new Vector3();
const tmpRotation = new Quaternion();
const tmpSpin = new Quaternion();
const tmpScale = new Vector3();
const yAxis = new Vector3(0, 1, 0);
const a = new Vector3();
const b = new Vector3();

function write(out: Float32Array, index: number) {
  tmpMatrix.compose(tmpPosition, tmpRotation, tmpScale);
  tmpMatrix.toArray(out, index * 16);
}

/** Fill `frame` with the scene at progress `p` (clamped to 0…1). Same input → same output. */
export function computeFrame(rawP: number, layout: Layout, frame: Frame): Frame {
  const p = clamp01(rawP);

  layout.stones.forEach((stone, i) => {
    const t = easeInOutCubic(windowProgress(p, stone.start, STONE_TRAVEL));
    // Quadratic Bézier: scatter → control → target.
    a.copy(stone.scatter).lerp(stone.control, t);
    b.copy(stone.control).lerp(stone.target, t);
    tmpPosition.copy(a).lerp(b, t);
    tmpRotation.copy(stone.startRotation).slerp(stone.endRotation, t);
    tmpSpin.setFromAxisAngle(yAxis, (1 - t) * stone.spin * Math.PI);
    tmpRotation.multiply(tmpSpin);
    tmpScale.setScalar(stone.size);
    write(frame.stones, i);

    const grow = windowProgress(
      p,
      SETTING_START + SETTING_STAGGER * (1 - Math.abs(stone.u)),
      SETTING_GROW,
    );
    tmpPosition.copy(stone.target);
    tmpRotation.copy(stone.endRotation).multiply(RING_TO_GIRDLE);
    tmpScale.setScalar(stone.size * 1.12 * Math.max(0, easeOutBack(grow)) * (grow > 0 ? 1 : 0));
    write(frame.settings, i);
  });

  layout.links.forEach((link, j) => {
    const grow = windowProgress(p, link.start, LINK_GROW);
    tmpPosition.copy(link.position);
    tmpRotation.copy(link.rotation);
    tmpScale.setScalar(link.scale * Math.max(0, easeOutBack(grow)) * (grow > 0 ? 1 : 0));
    write(frame.links, j);
  });

  // The whole piece turns from a three-quarter view to face the viewer as it completes.
  frame.turn = -0.55 * (1 - easeOutCubic(p));
  return frame;
}
