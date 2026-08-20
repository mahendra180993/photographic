"""Shared helpers: upload paths, image metadata, tokens, client info."""

import os
import secrets
import string
import uuid
from datetime import timedelta

from django.utils import timezone
from django.utils.text import slugify

ALPHABET = string.ascii_uppercase + string.digits
AMBIGUOUS = {"0", "O", "1", "I"}
SAFE_ALPHABET = "".join(ch for ch in ALPHABET if ch not in AMBIGUOUS)


def generate_access_code(length=8):
    """Human friendly, non-ambiguous share code (e.g. `K7HRPX29`)."""
    return "".join(secrets.choice(SAFE_ALPHABET) for _ in range(length))


def generate_token(length=40):
    return secrets.token_urlsafe(length)[:length]


def unique_filename(filename):
    name, ext = os.path.splitext(filename or "image.jpg")
    return f"{slugify(name)[:60] or 'file'}-{uuid.uuid4().hex[:10]}{ext.lower()}"


def gallery_image_path(instance, filename):
    gallery = getattr(instance, "gallery", None)
    folder = getattr(gallery, "uuid", uuid.uuid4())
    return f"galleries/{folder}/{unique_filename(filename)}"


def gallery_cover_path(instance, filename):
    return f"galleries/{instance.uuid}/cover/{unique_filename(filename)}"


def portfolio_image_path(instance, filename):
    return f"portfolio/{timezone.now():%Y/%m}/{unique_filename(filename)}"


def portfolio_cover_path(instance, filename):
    return f"portfolio/categories/{unique_filename(filename)}"


def service_image_path(instance, filename):
    return f"services/{unique_filename(filename)}"


def team_photo_path(instance, filename):
    return f"team/{unique_filename(filename)}"


def testimonial_photo_path(instance, filename):
    return f"testimonials/{unique_filename(filename)}"


def branding_path(instance, filename):
    return f"branding/{unique_filename(filename)}"


def avatar_path(instance, filename):
    return f"avatars/{unique_filename(filename)}"


def read_image_dimensions(fieldfile):
    """Return (width, height) for an ImageFieldFile, or (0, 0) if unreadable."""
    try:
        from PIL import Image

        fieldfile.open()
        with Image.open(fieldfile) as img:
            return int(img.width), int(img.height)
    except Exception:  # noqa: BLE001 - metadata is best-effort only
        return 0, 0
    finally:
        try:
            fieldfile.close()
        except Exception:  # noqa: BLE001
            pass


def human_filesize(num_bytes):
    value = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def get_client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    if request is None:
        return ""
    return (request.META.get("HTTP_USER_AGENT") or "")[:400]


def default_expiry(days=None):
    from django.conf import settings

    days = days if days is not None else getattr(settings, "GALLERY_DEFAULT_EXPIRY_DAYS", 90)
    return timezone.now() + timedelta(days=days)