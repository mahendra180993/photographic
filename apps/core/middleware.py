"""Project middleware: maintenance mode and last-activity tracking."""

from django.conf import settings
from django.shortcuts import render
from django.utils import timezone

EXEMPT_PREFIXES = ("/studio/", "/accounts/", "/static/", "/media/", "/health/", "/robots.txt")


class MaintenanceModeMiddleware:
    """Shows a holding page to the public when the studio flips the switch."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_hold(request):
            from apps.cms.models import WebsiteSettings

            site = WebsiteSettings.load()
            response = render(request, "errors/maintenance.html", {"site": site}, status=503)
            response["Retry-After"] = "3600"
            return response
        return self.get_response(request)

    def _should_hold(self, request):
        path = request.path
        if path.startswith(EXEMPT_PREFIXES):
            return False
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.has_studio_access:
            return False
        try:
            from apps.cms.models import WebsiteSettings

            return WebsiteSettings.objects.filter(pk=1, is_maintenance=True).exists()
        except Exception:  # noqa: BLE001 - never block requests on a settings lookup
            return False


class LastActivityMiddleware:
    """Records a coarse 'last seen' timestamp without hammering the DB."""

    THROTTLE_SECONDS = 300

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            last = user.last_activity_at
            now = timezone.now()
            if last is None or (now - last).total_seconds() > self.THROTTLE_SECONDS:
                try:
                    user.touch_activity()
                except Exception:  # noqa: BLE001
                    pass
        return response