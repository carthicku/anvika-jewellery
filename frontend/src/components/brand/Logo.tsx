/**
 * The brand wordmark, drawn as vector shapes: thin geometric lowercase letters with a stacked-dots
 * "i", and "FINE JEWELLERY" in wide-spaced capitals tucked under the right-hand letters (starting
 * under the "n", ending under the last "a"). Colour follows the surrounding text (`currentColor`),
 * so it works on both the ivory header and the dark footer. Self-contained: no font download.
 *
 * Coordinates are in a design grid taken from the brand reference sheet: baseline 553, x-height top
 * 448, "k" ascender 417. Stroke weights follow the reference (thin arcs, thicker right stems).
 */
import { cn } from '@/lib/cn';

const THIN = 4.5;

/**
 * The shared arch of "a" and "n": a half circle whose stroke is thin on the left and thick on the
 * right (outer circle r = 54, inner ellipse offset to the left), plus the straight stems below it.
 */
function Arch({ cx, left, right }: { cx: number; left: number; right: number }) {
  const outerL = cx - 54;
  const outerR = cx + 54;
  const innerL = outerL + left;
  const innerR = outerR - right;
  const rx = (innerR - innerL) / 2;
  const d = [
    `M ${String(outerL)} 502`,
    'A 54 54 0 0 1',
    `${String(outerR)} 502`,
    `L ${String(innerR)} 502`,
    `A ${String(rx)} 48 0 0 0 ${String(innerL)} 502 Z`,
  ].join(' ');
  return (
    <>
      <path d={d} fill="currentColor" />
      <rect x={innerR} y="502" width={right} height="51" fill="currentColor" />
    </>
  );
}

/** One "a": the arch with a thin bowl curling round underneath. Drawn at x = 114, shifted by dx. */
function LetterA({ dx }: { dx: number }) {
  return (
    <g transform={`translate(${String(dx)} 0)`}>
      <Arch cx={168} left={7} right={13} />
      <path
        d="M 117.5 502 A 50.5 50.5 0 0 0 190 548"
        fill="none"
        stroke="currentColor"
        strokeWidth={7}
        strokeLinecap="round"
      />
    </g>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="104 408 800 220"
      aria-hidden="true"
      focusable="false"
      className={cn('block h-auto', className)}
    >
      <LetterA dx={0} />

      {/* n: thin left stem, arch, thick right stem */}
      <Arch cx={330} left={4} right={13} />
      <rect x="276" y="502" width="4" height="51" fill="currentColor" />

      {/* v: thick left stroke, thin right stroke */}
      <path d="M 427 448 L 438 448 L 481 553 L 471 553 Z" fill="currentColor" />
      <path d="M 519 448 L 472 553" fill="none" stroke="currentColor" strokeWidth={THIN} />

      {/* i: three stacked dots, the middle one larger */}
      <circle cx="584.5" cy="452" r="10.5" fill="currentColor" />
      <circle cx="584.5" cy="497.5" r="15.5" fill="currentColor" />
      <circle cx="584.5" cy="542" r="11" fill="currentColor" />

      {/* k: tall thick stem, thin upper arm, thicker lower leg */}
      <rect x="659" y="417" width="10.5" height="136" fill="currentColor" />
      <path d="M 672 496 L 741 460" fill="none" stroke="currentColor" strokeWidth={THIN} />
      <path d="M 669 497 L 680 489 L 746 553 L 733 553 Z" fill="currentColor" />

      <LetterA dx={672} />

      {/* Tagline: spans exactly from under the "n" to the right edge of the last "a". */}
      <text
        x="368"
        y="615"
        textLength="525"
        lengthAdjust="spacing"
        fill="currentColor"
        fontFamily="'Inter Variable', system-ui, sans-serif"
        fontWeight="350"
        fontSize="32"
      >
        FINE JEWELLERY
      </text>
    </svg>
  );
}
