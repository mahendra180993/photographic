"""Public portfolio: categories and images."""

from django.db import models
from django.urls import reverse

from apps.common.models import OrderedActiveModel, SluggedModel, TimeStampedModel, UUIDModel
from apps.common.utils import portfolio_cover_path, portfolio_image_path, read_image_dimensions


class PortfolioCategory(UUIDModel, TimeStampedModel, OrderedActiveModel, SluggedModel):
    slug_source_field = "name"

    name = models.CharField(max_length=140, unique=True)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to=portfolio_cover_path, blank=True, null=True)
    accent_color = models.CharField(max_length=9, blank=True, default="#D4AF37")
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta(OrderedActiveModel.Meta):
        verbose_name_plural = "portfolio categories"
        ordering = ("order", "name")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("website:portfolio_detail", args=[self.slug])

    @property
    def image_count(self):
        return self.images.filter(is_active=True).count()

    @property
    def preview_image(self):
        if self.cover_image:
            return self.cover_image
        first = self.images.filter(is_active=True).first()
        return first.image if first else None


class PortfolioImage(UUIDModel, TimeStampedModel, OrderedActiveModel):
    category = models.ForeignKey(
        PortfolioCategory,
        on_delete=models.CASCADE,
        related_name="images",
    )
    title = models.CharField(max_length=180, blank=True)
    image = models.ImageField(upload_to=portfolio_image_path)
    caption = models.TextField(blank=True)
    alt_text = models.CharField(max_length=220, blank=True)
    location = models.CharField(max_length=160, blank=True)
    shot_on = models.DateField(blank=True, null=True)
    credits = models.CharField(max_length=240, blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta(OrderedActiveModel.Meta):
        ordering = ("order", "-created_at")
        indexes = [models.Index(fields=["category", "order"])]

    def __str__(self):
        return self.title or f"Image #{self.pk}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and not self.width:
            width, height = read_image_dimensions(self.image)
            if width:
                PortfolioImage.objects.filter(pk=self.pk).update(width=width, height=height)
                self.width, self.height = width, height

    @property
    def display_alt(self):
        return self.alt_text or self.title or f"{self.category.name} photograph"

    @property
    def is_portrait(self):
        return bool(self.height and self.width and self.height > self.width)