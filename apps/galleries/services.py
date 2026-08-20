"""Domain helpers for gallery access, logging and downloads."""

import io
import os
import zipfile

from django.conf import settings
from django.utils import timezone

from apps.common.utils import get_client_ip, get_user_agent


def session_unlocked_ids(request):
    return set(request.session.get(settings.GALLERY_ACCESS_SESSION_KEY, []))


def unlock_gallery_in_session(request, gallery):
    unlocked = session_unlocked_ids(request)
    unlocked.add(str(gallery.uuid))
    request.session[settings.GALLERY_ACCESS_SESSION_KEY] = list(unlocked)
    request.session.modified = True


def gallery_unlocked(request, gallery):
    return str(gallery.uuid) in session_unlocked_ids(request)


def log_access(gallery, request=None, action="view", note="", user=None):
    from .models import GalleryAccessLog

    resolved_user = user
    if resolved_user is None and request is not None:
        resolved_user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    return GalleryAccessLog.objects.create(
        gallery=gallery,
        user=resolved_user,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        path=(request.get_full_path()[:300] if request else ""),
        note=note[:240],
    )


def record_download(gallery, request=None, image=None, kind="single", item_count=1):
    from .models import DownloadHistory

    user = request.user if request and request.user.is_authenticated else None
    customer = getattr(user, "customer_profile", None) if user else None
    entry = DownloadHistory.objects.create(
        gallery=gallery,
        image=image,
        customer=customer or gallery.customer,
        user=user,
        download_type=kind,
        item_count=item_count,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    gallery.register_download(item_count)
    if image is not None:
        type(image).objects.filter(pk=image.pk).update(download_count=image.download_count + 1)
    log_access(gallery, request=request, action="download", note=f"{kind} x{item_count}")
    return entry


def build_gallery_zip(gallery, images=None, max_images=None):
    """Build an in-memory ZIP archive of the gallery originals."""
    max_images = max_images or getattr(settings, "GALLERY_ZIP_MAX_IMAGES", 300)
    queryset = images if images is not None else gallery.images.filter(is_hidden=False, allow_download=True)
    buffer = io.BytesIO()
    included = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, item in enumerate(queryset[:max_images], start=1):
            if not item.image:
                continue
            try:
                item.image.open("rb")
                data = item.image.read()
            except Exception:  # noqa: BLE001 - skip unreadable files
                continue
            finally:
                try:
                    item.image.close()
                except Exception:  # noqa: BLE001
                    pass
            name = os.path.basename(item.image.name) or f"image-{index}.jpg"
            archive.writestr(f"{gallery.slug}/{index:03d}-{name}", data)
            included += 1
        archive.writestr(
            f"{gallery.slug}/README.txt",
            (
                f"{gallery.title}\n"
                f"Delivered by MS Photo Studio\n"
                f"Downloaded: {timezone.now():%Y-%m-%d %H:%M} UTC\n"
                f"Images included: {included}\n"
            ),
        )
    buffer.seek(0)
    return buffer, included