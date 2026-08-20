"""Sitemap definitions for the public website."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        return [
            "website:home",
            "website:about",
            "website:portfolio",
            "website:services",
            "website:testimonials",
            "website:contact",
        ]

    def location(self, item):
        return reverse(item)


class PortfolioSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        from apps.portfolio.models import PortfolioCategory

        return PortfolioCategory.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class ServiceSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        from apps.services.models import Service

        return Service.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViewSitemap,
    "portfolio": PortfolioSitemap,
    "services": ServiceSitemap,
}