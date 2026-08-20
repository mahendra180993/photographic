"""Infrastructure views: robots.txt, health check and error pages."""

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View


class RobotsTxtView(View):
    def get(self, request, *args, **kwargs):
        from apps.cms.models import SEOSettings

        seo = SEOSettings.load()
        body = seo.robots_txt or "User-agent: *\nAllow: /\n"
        domain = seo.canonical_domain or request.build_absolute_uri("/").rstrip("/")
        if "Sitemap:" not in body:
            body = f"{body.rstrip()}\n\nSitemap: {domain.rstrip('/')}/sitemap.xml\n"
        return HttpResponse(body, content_type="text/plain; charset=utf-8")


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        from django.db import connection

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            database = "ok"
        except Exception as exc:  # noqa: BLE001
            database = f"error: {exc}"
        return JsonResponse({"status": "ok", "database": database})


def page_not_found(request, exception=None, template_name="errors/404.html"):
    return render(request, template_name, status=404)


def server_error(request, template_name="errors/500.html"):
    return render(request, template_name, status=500)


def permission_denied(request, exception=None, template_name="errors/403.html"):
    return render(request, template_name, status=403)


def bad_request(request, exception=None, template_name="errors/404.html"):
    return render(request, template_name, status=400)