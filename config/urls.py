"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.sitemaps import SITEMAPS
from apps.core.views import HealthCheckView, RobotsTxtView

urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("client/", include("apps.galleries.urls")),
    path("studio/", include("apps.dashboard.urls")),
    path("robots.txt", RobotsTxtView.as_view(), name="robots_txt"),
    path("health/", HealthCheckView.as_view(), name="health"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("apps.website.urls")),
]

handler400 = "apps.core.views.bad_request"
handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")