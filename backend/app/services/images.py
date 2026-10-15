"""Product photo processing (docs/architecture/SECURITY_MODEL.md threat 14).

Uploads are decoded with Pillow and RE-ENCODED as WebP in a few widths. Re-encoding drops any
embedded scripts, EXIF/GPS metadata and polyglot payloads; only JPEG, PNG and WebP are accepted,
and oversized ("decompression bomb") images are refused.
"""

from __future__ import annotations

import io
import secrets
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import ValidationFailed

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000  # ~ 8000 × 5000
MIN_SIDE = 400
WIDTHS = (400, 800, 1600)
QUALITY = 82


@dataclass
class ProcessedImage:
    width: int
    height: int
    # width → WebP bytes (never wider than the original)
    renditions: dict[int, bytes]


def _invalid(message: str) -> ValidationFailed:
    return ValidationFailed({"file": message})


def process(data: bytes) -> ProcessedImage:
    if len(data) > MAX_BYTES:
        raise _invalid("The image is larger than 10 MB.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            width, height = probe.size
            probe.verify()  # structural check before decoding pixels
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise _invalid("This file isn't a readable JPEG, PNG or WebP image.") from exc
    except Image.DecompressionBombError as exc:  # pragma: no cover - covered by the size check
        raise _invalid("This image is too large.") from exc
    if fmt not in ALLOWED_FORMATS:
        raise _invalid("Upload a JPEG, PNG or WebP image.")
    if width * height > MAX_PIXELS:
        raise _invalid("This image has too many pixels. Please resize it below 40 megapixels.")
    if min(width, height) < MIN_SIDE:
        raise _invalid(f"The image must be at least {MIN_SIDE} pixels on its shorter side.")

    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        image = image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")
        width, height = image.size
        # Standard widths below the original, plus the original itself (capped at the largest).
        targets = sorted({w for w in WIDTHS if w < width} | {min(width, WIDTHS[-1])})
        renditions: dict[int, bytes] = {}
        for target in targets:
            size = (target, round(height * target / width))
            resized = image if size == image.size else image.resize(size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            resized.save(buffer, "WEBP", quality=QUALITY, method=4)  # no EXIF passed → stripped
            renditions[target] = buffer.getvalue()
    return ProcessedImage(width=width, height=height, renditions=renditions)


def new_image_key(product_id: str) -> str:
    return f"products/{product_id}/{secrets.token_hex(8)}"
