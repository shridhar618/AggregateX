"""Reference-image validation.

Uploaded reference images are validated, re-encoded (which strips EXIF/GPS and
any trailing payload), passed to the generator for that one request, and never
written to disk. No face detection, recognition or attribute inference is done.
"""

from __future__ import annotations

import base64
import binascii
import io
import re

from PIL import Image, UnidentifiedImageError

from ..config import get_settings

ALLOWED = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
MAGIC = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/webp": [b"RIFF"],
}
DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[a-z]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)$")


class UploadError(ValueError):
    pass


def validate_reference_image(data_url: str) -> tuple[bytes, str]:
    """Return (clean_png_bytes, 'image/png') or raise UploadError."""
    settings = get_settings()
    m = DATA_URL_RE.match(data_url or "")
    if not m:
        raise UploadError("Reference image must be a base64 data URL.")
    mime = m.group("mime")
    if mime not in ALLOWED:
        raise UploadError("Unsupported image type. Use PNG, JPEG or WebP.")
    try:
        raw = base64.b64decode(m.group("data"), validate=False)
    except (binascii.Error, ValueError):
        raise UploadError("Reference image data is not valid base64.") from None
    if len(raw) == 0:
        raise UploadError("Reference image is empty.")
    if len(raw) > settings.max_upload_bytes:
        raise UploadError(f"Reference image is larger than {settings.max_upload_bytes // (1024 * 1024)} MB.")
    if not any(raw.startswith(sig) for sig in MAGIC[mime]) or (mime == "image/webp" and raw[8:12] != b"WEBP"):
        raise UploadError("File contents do not match the declared image type.")

    Image.MAX_IMAGE_PIXELS = settings.max_upload_pixels
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(raw)) as img:
            if img.format != ALLOWED[mime]:
                raise UploadError("File contents do not match the declared image type.")
            if img.width * img.height > settings.max_upload_pixels:
                raise UploadError("Reference image dimensions are too large.")
            img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
    except UploadError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise UploadError("Reference image could not be decoded safely.") from None
    return buf.getvalue(), "image/png"
