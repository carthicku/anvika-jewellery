"""Generate the original line-art placeholder illustrations used by the sample catalogue.

Usage (repository root):  py -3.13 scripts/generate_placeholders.py
Output: frontend/public/images/placeholders/*.svg  (committed; regenerate only if this script changes)

They are deliberately simple, clearly labelled "SAMPLE IMAGE", and never presented as photographs
of real inventory (docs/ASSUMPTIONS_AND_DECISIONS.md B7).
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "images" / "placeholders"
GOLD = "#B08D57"
GOLD_SOFT = "#D9C4A0"
BG = "#F3EEE6"
CAPTION = "#6F695F"

# Each drawing is authored on an 800×800 canvas centred at (400, 400).
DRAWINGS: dict[str, tuple[str, str]] = {
    "ring-solitaire": (
        "a solitaire ring",
        """
        <ellipse cx="400" cy="470" rx="170" ry="190"/>
        <ellipse cx="400" cy="470" rx="146" ry="166" stroke="{soft}"/>
        <path d="M340 292 L400 236 L460 292 L400 330 Z"/>
        <path d="M340 292 L460 292 M400 236 L380 292 L400 330 L420 292 Z" stroke="{soft}"/>
        <path d="M362 300 L370 322 M438 300 L430 322"/>
        """,
    ),
    "ring-band": (
        "a gold band ring",
        """
        <ellipse cx="400" cy="400" rx="210" ry="120"/>
        <ellipse cx="400" cy="372" rx="178" ry="96" stroke="{soft}"/>
        <path d="M190 400 L190 440 M610 400 L610 440"/>
        <path d="M190 440 A210 120 0 0 0 610 440"/>
        <path d="M250 455 Q400 520 550 455" stroke="{soft}"/>
        """,
    ),
    "earrings-stud": (
        "a pair of stud earrings",
        """
        <g transform="translate(-130 0)">
          <circle cx="400" cy="400" r="62"/>
          <circle cx="400" cy="400" r="26" stroke="{soft}"/>
          <path d="M400 338 L400 312 M462 400 L488 400 M400 462 L400 488 M338 400 L312 400"/>
        </g>
        <g transform="translate(130 0)">
          <circle cx="400" cy="400" r="62"/>
          <circle cx="400" cy="400" r="26" stroke="{soft}"/>
          <path d="M400 338 L400 312 M462 400 L488 400 M400 462 L400 488 M338 400 L312 400"/>
        </g>
        """,
    ),
    "earrings-jhumka": (
        "a pair of jhumka earrings",
        """
        <g transform="translate(-140 0)">
          <circle cx="400" cy="230" r="26"/>
          <path d="M400 256 L400 300"/>
          <path d="M320 420 Q320 300 400 300 Q480 300 480 420 Z"/>
          <path d="M320 420 Q400 450 480 420" stroke="{soft}"/>
          <path d="M335 432 L335 470 M367 440 L367 486 M400 444 L400 492 M433 440 L433 486 M465 432 L465 470"/>
          <circle cx="335" cy="478" r="7"/><circle cx="367" cy="494" r="7"/><circle cx="400" cy="500" r="7"/>
          <circle cx="433" cy="494" r="7"/><circle cx="465" cy="478" r="7"/>
        </g>
        <g transform="translate(140 0)">
          <circle cx="400" cy="230" r="26"/>
          <path d="M400 256 L400 300"/>
          <path d="M320 420 Q320 300 400 300 Q480 300 480 420 Z"/>
          <path d="M320 420 Q400 450 480 420" stroke="{soft}"/>
          <path d="M335 432 L335 470 M367 440 L367 486 M400 444 L400 492 M433 440 L433 486 M465 432 L465 470"/>
          <circle cx="335" cy="478" r="7"/><circle cx="367" cy="494" r="7"/><circle cx="400" cy="500" r="7"/>
          <circle cx="433" cy="494" r="7"/><circle cx="465" cy="478" r="7"/>
        </g>
        """,
    ),
    "necklace": (
        "a gold necklace",
        """
        <path d="M170 170 Q170 560 400 600 Q630 560 630 170"/>
        <path d="M200 170 Q205 520 400 560 Q595 520 600 170" stroke="{soft}"/>
        <path d="M330 590 L400 660 L470 590"/>
        <ellipse cx="400" cy="690" rx="34" ry="42"/>
        <path d="M244 470 L262 490 M556 470 L538 490 M300 540 L312 566 M500 540 L488 566"/>
        """,
    ),
    "pendant": (
        "a pendant on a fine chain",
        """
        <path d="M230 140 L400 470 L570 140" stroke-dasharray="2 10"/>
        <circle cx="400" cy="486" r="16"/>
        <path d="M400 502 Q330 590 400 680 Q470 590 400 502 Z"/>
        <path d="M400 540 Q365 592 400 640 Q435 592 400 540" stroke="{soft}"/>
        """,
    ),
    "bangle": (
        "a gold bangle",
        """
        <circle cx="400" cy="400" r="230"/>
        <circle cx="400" cy="400" r="198" stroke="{soft}"/>
        <circle cx="400" cy="400" r="214" stroke-dasharray="4 18" stroke="{soft}"/>
        """,
    ),
    "bracelet": (
        "a link bracelet",
        """
        <g stroke-width="2.6">
          <ellipse cx="400" cy="200" rx="40" ry="26"/><ellipse cx="530" cy="250" rx="40" ry="26" transform="rotate(35 530 250)"/>
          <ellipse cx="600" cy="370" rx="40" ry="26" transform="rotate(80 600 370)"/><ellipse cx="575" cy="505" rx="40" ry="26" transform="rotate(-55 575 505)"/>
          <ellipse cx="470" cy="590" rx="40" ry="26" transform="rotate(-20 470 590)"/><ellipse cx="330" cy="590" rx="40" ry="26" transform="rotate(20 330 590)"/>
          <ellipse cx="225" cy="505" rx="40" ry="26" transform="rotate(55 225 505)"/><ellipse cx="200" cy="370" rx="40" ry="26" transform="rotate(100 200 370)"/>
          <ellipse cx="270" cy="250" rx="40" ry="26" transform="rotate(-35 270 250)"/>
        </g>
        """,
    ),
    "chain": (
        "a gold chain",
        """
        <path d="M150 260 Q400 760 650 260" stroke-width="10" stroke-dasharray="14 8" stroke-linecap="butt"/>
        <path d="M150 260 Q400 760 650 260" stroke="{soft}" stroke-width="2"/>
        <rect x="620" y="226" width="44" height="22" rx="8"/>
        """,
    ),
    "mangalsutra": (
        "a mangalsutra",
        """
        <path d="M180 160 Q190 520 400 560 Q610 520 620 160" stroke="#3B3833" stroke-width="7" stroke-dasharray="1 15"/>
        <path d="M195 160 Q205 500 400 540 Q595 500 605 160" stroke="{soft}"/>
        <path d="M360 560 L400 600 L440 560"/>
        <circle cx="372" cy="640" r="30"/><circle cx="428" cy="640" r="30"/>
        """,
    ),
}


def svg(name: str, label: str, body: str, *, zoom: float, width: int, height: int) -> str:
    cx, cy = width / 2, height / 2 - (40 if height > width else 20)
    scale = min(width, height) / 800 * zoom
    shapes = body.replace("{soft}", GOLD_SOFT)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Sample illustration of {label}">
  <title>Sample illustration of {label}</title>
  <defs>
    <radialGradient id="light-{name}" cx="50%" cy="40%" r="65%">
      <stop offset="0" stop-color="#FBF8F3"/>
      <stop offset="1" stop-color="{BG}"/>
    </radialGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#light-{name})"/>
  <g transform="translate({cx - 400 * scale:.1f} {cy - 400 * scale:.1f}) scale({scale:.3f})" fill="none" stroke="{GOLD}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
{shapes}
  </g>
  <text x="{width / 2:.0f}" y="{height - 44}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{max(14, int(width / 40))}" letter-spacing="6" fill="{CAPTION}">SAMPLE IMAGE</text>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for name, (label, body) in DRAWINGS.items():
        (OUT / f"{name}.svg").write_text(
            svg(name, label, body, zoom=0.9, width=800, height=1000), encoding="utf-8"
        )
        (OUT / f"{name}-detail.svg").write_text(
            svg(f"{name}-d", f"{label} (detail)", body, zoom=1.45, width=800, height=1000),
            encoding="utf-8",
        )
        count += 2
    hero_body = DRAWINGS["necklace"][1]
    (OUT / "hero.svg").write_text(
        svg("hero", "a gold necklace", hero_body, zoom=0.95, width=1600, height=1000),
        encoding="utf-8",
    )
    print(f"Wrote {count + 1} placeholder illustrations to {OUT}")


if __name__ == "__main__":
    main()
