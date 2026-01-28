from __future__ import annotations

import io
from typing import Tuple

from PIL import Image

try:
    import tinify  # type: ignore
except Exception:
    tinify = None  # pragma: no cover


def compress_image(
    raw_bytes: bytes,
    tinify_api_key: str = "",
    max_size_px: int = 1200,
    jpeg_quality: int = 82,
) -> Tuple[bytes, str]:
    """
    Returns (compressed_bytes, mimetype).

    Default: Pillow optimize to JPEG.
    Optional: if tinify_api_key is set and tinify is available, run TinyPNG after Pillow.
    """
    img = Image.open(io.BytesIO(raw_bytes))
    img = img.convert("RGB")

    # Resize down if needed
    w, h = img.size
    scale = min(1.0, max_size_px / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))

    out = io.BytesIO()
    img.save(out, format="JPEG", optimize=True, quality=jpeg_quality)
    pillow_bytes = out.getvalue()

    # Optional TinyPNG
    if tinify_api_key and tinify is not None:
        try:
            tinify.key = tinify_api_key
            source = tinify.from_buffer(pillow_bytes)
            tinified = source.to_buffer()
            return tinified, "image/jpeg"
        except Exception:
            # Fall back to Pillow output if TinyPNG fails
            return pillow_bytes, "image/jpeg"

    return pillow_bytes, "image/jpeg"
