"""Reusable abstract models shared across the platform."""

import uuid

from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Adds self-managed created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        get_latest_by = "created_at"


class UUIDModel(models.Model):
    """Adds a public, non-guessable identifier alongside the integer PK."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    class Meta:
        abstract = True


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)


class ActiveManager(models.Manager.from_queryset(ActiveQuerySet)):
    pass


class OrderedActiveModel(models.Model):
    """Common `is_active` + `order` combo used by every CMS-style model."""

    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    objects = ActiveManager()

    class Meta:
        abstract = True
        ordering = ("order", "-id")


class SluggedModel(models.Model):
    """Auto-populates a unique slug from `slug_source_field`."""

    slug_source_field = "title"

    slug = models.SlugField(max_length=180, unique=True, blank=True)

    class Meta:
        abstract = True

    def build_slug(self):
        base = slugify(getattr(self, self.slug_source_field, "") or "")[:150]
        if not base:
            base = str(uuid.uuid4())[:8]
        candidate = base
        model = self.__class__
        counter = 2
        while model.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.build_slug()
        super().save(*args, **kwargs)


class SingletonModel(models.Model):
    """A model that only ever has one row (pk=1)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - singletons are permanent
        return None

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj