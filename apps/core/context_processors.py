"""Injects brand settings and navigation into every template render."""

from django.conf import settings
from django.db.utils import DatabaseError, OperationalError, ProgrammingError

_DB_ERRORS = (DatabaseError, OperationalError, ProgrammingError)


def _safe_load(model):
    """Load a singleton without exploding before the first migration."""
    try:
        return model.load()
    except _DB_ERRORS:
        return model()
    except Exception:  # noqa: BLE001
        return model()


def site_context(request):
    from apps.cms.models import SEOSettings, WebsiteSettings

    site = _safe_load(WebsiteSettings)
    seo = _safe_load(SEOSettings)

    return {
        "site": site,
        "seo": seo,
        "BRAND_NAME": getattr(site, "site_name", None) or settings.STUDIO_BRAND_NAME,
        "BRAND_GOLD": getattr(site, "accent_color", None) or settings.STUDIO_BRAND_GOLD,
        "SITE_DOMAIN": settings.SITE_DOMAIN,
        "DEBUG": settings.DEBUG,
    }


def navigation(request):
    from apps.notifications.models import Notification

    user = getattr(request, "user", None)
    unread = 0
    if user is not None and user.is_authenticated:
        try:
            unread = Notification.objects.for_user(user).unread().count()
        except _DB_ERRORS:
            unread = 0

    return {
        "main_nav": [
            {"label": "Home", "url_name": "website:home", "key": "home"},
            {"label": "Portfolio", "url_name": "website:portfolio", "key": "portfolio"},
            {"label": "Services", "url_name": "website:services", "key": "services"},
            {"label": "Studio", "url_name": "website:about", "key": "about"},
            {"label": "Journal", "url_name": "website:testimonials", "key": "testimonials"},
            {"label": "Contact", "url_name": "website:contact", "key": "contact"},
        ],
        "unread_notifications": unread,
    }