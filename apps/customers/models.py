"""Customer and photographer records."""

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.common.models import ActiveManager, TimeStampedModel, UUIDModel
from apps.common.utils import avatar_path


class Photographer(UUIDModel, TimeStampedModel):
    """A shooter on the studio roster; optionally linked to a login."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photographer_profile",
    )
    display_name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    title = models.CharField(max_length=120, blank=True, default="Photographer")
    bio = models.TextField(blank=True)
    specialties = models.CharField(
        max_length=240,
        blank=True,
        help_text="Comma separated, e.g. Weddings, Editorial, Fine Art",
    )
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    instagram = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    avatar = models.ImageField(upload_to=avatar_path, blank=True, null=True)
    is_lead = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    objects = ActiveManager()

    class Meta:
        ordering = ("order", "display_name")
        verbose_name = "photographer"
        verbose_name_plural = "photographers"

    def __str__(self):
        return self.display_name

    @property
    def specialty_list(self):
        return [item.strip() for item in self.specialties.split(",") if item.strip()]

    @property
    def gallery_count(self):
        return self.galleries.count()


class CustomerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=Customer.Status.ACTIVE)

    def with_gallery_counts(self):
        return self.annotate(gallery_total=models.Count("galleries", distinct=True))

    def search(self, term):
        if not term:
            return self
        return self.filter(
            models.Q(full_name__icontains=term)
            | models.Q(email__icontains=term)
            | models.Q(phone__icontains=term)
            | models.Q(company__icontains=term)
        )


class Customer(UUIDModel, TimeStampedModel):
    """A studio client. `user` is the login they use for the client area."""

    class Status(models.TextChoices):
        LEAD = "lead", "Lead"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    class Kind(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        COUPLE = "couple", "Couple"
        FAMILY = "family", "Family"
        CORPORATE = "corporate", "Corporate"
        BRAND = "brand", "Brand"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
    )
    full_name = models.CharField(max_length=160, db_index=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    customer_type = models.CharField(max_length=20, choices=Kind.choices, default=Kind.INDIVIDUAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    address = models.CharField(max_length=240, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)

    assigned_photographer = models.ForeignKey(
        Photographer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )
    tags = models.CharField(max_length=240, blank=True, help_text="Comma separated labels")
    notes = models.TextField(blank=True)
    marketing_opt_in = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customers",
    )

    objects = CustomerQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("dashboard:customer_detail", args=[self.pk])

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def initials(self):
        parts = [p for p in self.full_name.split() if p]
        if not parts:
            return "LA"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def has_login(self):
        return self.user_id is not None

    @property
    def active_galleries(self):
        return self.galleries.filter(status__in=["ready", "delivered"])