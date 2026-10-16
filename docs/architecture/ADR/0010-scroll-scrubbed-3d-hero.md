# ADR-0010: Scroll-scrubbed 3D necklace hero (three.js + React Three Fiber + GSAP ScrollTrigger)

- Status: Accepted
- Date: 2026-10-16

## Context
The owner asked for a home-page hero in which scattered diamonds assemble into a gold necklace as
the visitor scrolls, and come apart again when they scroll back — fully reversible, pinned for a
controlled distance, driven only by scroll (no autoplay, timers or one-way entrance animations),
working across resizes and respecting reduced motion. The storefront's initial JavaScript budget
is < 200 kB gzip (currently 93 kB), and the headline must stay the fast first paint.

## Decision
* **Rendering**: three.js 0.186 through `@react-three/fiber` 9 (React 19 support). Three instanced
  meshes (stones, gold settings, chain links + bail), a locally generated studio reflection map
  (`RoomEnvironment`, no HDR download), on-demand rendering (`frameloop="demand"`): a frame is
  drawn only when progress or size changes.
* **Scroll control**: GSAP 3.15 `ScrollTrigger` with `pin` and `scrub: 0.6`, set up through
  `@gsap/react`'s `useGSAP` (automatic clean-up) and `gsap.matchMedia()` (live reduced-motion
  switching). The tween animates one number, `p` ∈ [0, 1].
* **Reversibility by construction**: `src/features/necklace/timeline.ts` computes the whole scene
  as a pure function of `p` (seeded layout; quadratic Bézier paths; per-element time windows).
  No state is carried between frames, so reverse scrolling replays the same frames exactly and any
  jump (resize, Home/End, scrollbar drag) shows the right frame immediately.
* **Loading**: the hero frame and copy are in the main bundle; `NecklaceStage` (three/R3F/GSAP) is
  a separate lazy chunk. Without WebGL the hero is the dark section with its text, unpinned.
* **Reduced motion**: no pin, no scrub; the finished necklace is shown as a still (`p = 1`).
* **Licence**: GSAP is free under its "Standard no-charge" licence, which allows commercial
  websites (it excludes building tools that compete with Webflow — not our case). three.js and
  R3F are MIT.

## Consequences
* The 3D chunk is downloaded on every home-page visit (see PERFORMANCE_REVIEW for size and
  Lighthouse impact); it does not block the headline.
* The necklace is a decorative illustration, not a product: no business facts are shown, and the
  canvas is `aria-hidden`.
* Tuning the animation means editing the constants in `timeline.ts`; its unit tests guarantee the
  start/end states, reversibility and progressive chain.
* `e2e/necklace.spec.ts` compares rendered pixels (forward vs backward), pinning, resize and
  reduced motion on the dev prototype (`/lab/necklace`, development builds only) and the home page.
