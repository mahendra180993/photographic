"""Studio service offerings / packages."""

from django.db import models
from django.urls import reverse

from apps.common.models import OrderedActiveModel, SluggedModel, TimeStampedModel, UUIDModel
from apps.common.utils import service_image_path


class Service(UUIDModel, TimeStampedModel, OrderedActiveModel, SluggedModel):
    slug_source_field = "title"

    title = models.CharField(max_length=160, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    short_description = models.CharField(max_length=320, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=60,
        blank=True,
        default="camera",
        help_text="Icon key rendered by the front-end (camera, ring, building, film...)",
    )
    image = models.ImageField(upload_to=service_image_path, blank=True, null=True)

    price_from = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=6, blank=True, default="EUR")
    price_unit = models.CharField(max_length=60, blank=True, default="per project")
    duration = models.CharField(max_length=80, blank=True, help_text="e.g. Full day / 6 hours")
    turnaround = models.CharField(max_length=80, blank=True, help_text="e.g. 3 weeks")

    features = models.TextField(
        blank=True,
        help_text="One feature per line - rendered as a checklist.",
    )
    deliverables = models.TextField(blank=True, help_text="One deliverable per line.")
    cta_label = models.CharField(max_length=60, blank=True, default="Enquire")
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta(OrderedActiveModel.Meta):
        ordering = ("order", "title")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("website:service_detail", args=[self.slug])

    @property
    def feature_list(self):
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    @property
    def deliverable_list(self):
        return [line.strip() for line in self.deliverables.splitlines() if line.strip()]

    @property
    def price_display(self):
        if self.price_from is None:
            return "On request"
        amount = f"{self.price_from:,.0f}"
        symbol = {"EUR": "EUR ", "USD": "$", "GBP": "GBP "}.get(self.currency, f"{self.currency} ")
        return f"from {symbol}{amount}"