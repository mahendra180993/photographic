"""Client galleries, images and access/download audit trails."""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.common.models import (
    ActiveManager,
    OrderedActiveModel,
    SluggedModel,
    TimeStampedModel,
    UUIDModel,
)
from apps.common.utils import (
    gallery_cover_path,
    gallery_image_path,
    generate_access_code,
    read_image_dimensions,
)


class GalleryCategory(UUIDModel, TimeStampedModel, OrderedActiveModel, SluggedModel):
    slug_source_field = "name"

    name = models.CharField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=9, blank=True, default="#D4AF37")

    class Meta(OrderedActiveModel.Meta):
        ordering = ("order", "name")
        verbose_name_plural = "gallery categories"

    def __str__(self):
        return self.name


class GalleryQuerySet(models.QuerySet):
    def live(self):
        now = timezone.now()
        return self.filter(status__in=[Gallery.Status.READY, Gallery.Status.DELIVERED]).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

    def for_customer(self, customer):
        if customer is None:
            return self.none()
        return self.filter(customer=customer)

    def expiring_soon(self, days=14):
        now = timezone.now()
        return self.filter(expires_at__isnull=False, expires_at__gt=now,
                           expires_at__lte=now + timezone.timedelta(days=days))

    def search(self, term):
        if not term:
            return self
        return self.filter(
            models.Q(title__icontains=term)
            | models.Q(customer__full_name__icontains=term)
            | models.Q(access_code__iexact=term)
        )


class Gallery(UUIDModel, TimeStampedModel, SluggedModel):
    """A delivery gallery assigned to a customer."""

    slug_source_field = "title"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready to share"
        DELIVERED = "delivered", "Delivered"
        ARCHIVED = "archived", "Archived"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private (client login only)"
        CODE = "code", "Shareable link + access code"
        PUBLIC = "public", "Public link"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    welcome_message = models.TextField(
        blank=True,
        help_text="Shown at the top of the client gallery page.",
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="galleries",
    )
    photographer = models.ForeignKey(
        "customers.Photographer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="galleries",
    )
    category = models.ForeignKey(
        GalleryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="galleries",
    )

    cover_image = models.ImageField(upload_to=gallery_cover_path, blank=True, null=True)
    event_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=180, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE)
    access_code = models.CharField(
        max_length=16,
        blank=True,
        db_index=True,
        help_text="Required when the gallery is shared by link.",
    )

    expires_at = models.DateTimeField(blank=True, null=True, db_index=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    allow_downloads = models.BooleanField(default=True)
    allow_bulk_download = models.BooleanField(default=True)
    allow_selection = models.BooleanField(default=True)
    allow_favorites = models.BooleanField(default=True)
    selection_limit = models.PositiveIntegerField(
        default=0,
        help_text="Maximum photos the client may select. 0 means unlimited.",
    )
    selection_deadline = models.DateField(blank=True, null=True)

    watermark_enabled = models.BooleanField(default=False)
    watermark_text = models.CharField(max_length=80, blank=True, default="LUMINA ATELIER")

    notify_customer = models.BooleanField(
        default=True,
        help_text="Email the client when this gallery is delivered.",
    )
    notified_at = models.DateTimeField(blank=True, null=True)

    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_galleries",
    )

    objects = GalleryQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "galleries"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.visibility != self.Visibility.PRIVATE and not self.access_code:
            self.access_code = generate_access_code()
        if self.status == self.Status.DELIVERED and self.delivered_at is None:
            self.delivered_at = timezone.now()
        super().save(*args, **kwargs)

    # -- urls -----------------------------------------------------------
    def get_absolute_url(self):
        return reverse("client:gallery_detail", args=[self.slug])

    def get_share_url(self):
        return reverse("client:gallery_share", args=[str(self.uuid)])

    def get_dashboard_url(self):
        return reverse("dashboard:gallery_detail", args=[self.pk])

    # -- state ----------------------------------------------------------
    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_live(self):
        return self.status in {self.Status.READY, self.Status.DELIVERED} and not self.is_expired

    @property
    def days_left(self):
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @property
    def selection_open(self):
        if not self.allow_selection or not self.is_live:
            return False
        if self.selection_deadline and self.selection_deadline < timezone.localdate():
            return False
        return True

    @property
    def image_count(self):
        return self.images.filter(is_hidden=False).count()

    @property
    def total_size(self):
        return self.images.aggregate(total=models.Sum("file_size"))["total"] or 0

    @property
    def selected_count(self):
        return self.selections.filter(is_selected=True).count()

    @property
    def cover(self):
        if self.cover_image:
            return self.cover_image
        image = self.images.filter(is_hidden=False).first()
        return image.image if image else None

    def register_view(self):
        Gallery.objects.filter(pk=self.pk).update(view_count=models.F("view_count") + 1)

    def register_download(self, amount=1):
        Gallery.objects.filter(pk=self.pk).update(
            download_count=models.F("download_count") + amount
        )

    def can_be_viewed_by(self, user):
        """Login-based access check (share-code access is handled separately)."""
        if not user or not user.is_authenticated:
            return False
        if user.has_studio_access:
            return True
        customer = getattr(user, "customer_profile", None)
        return customer is not None and customer.pk == self.customer_id

    def rotate_access_code(self):
        self.access_code = generate_access_code()
        self.save(update_fields=["access_code", "updated_at"])
        return self.access_code


class GalleryImage(UUIDModel, TimeStampedModel):
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=gallery_image_path)
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    alt_text = models.CharField(max_length=220, blank=True)
    filename = models.CharField(max_length=220, blank=True)

    order = models.PositiveIntegerField(default=0, db_index=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    file_size = models.BigIntegerField(default=0)

    is_cover = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False, db_index=True)
    is_highlight = models.BooleanField(default=False)
    allow_download = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_images",
    )

    class Meta:
        ordering = ("order", "id")
        indexes = [models.Index(fields=["gallery", "order"])]

    def __str__(self):
        return self.display_title

    def save(self, *args, **kwargs):
        if self.image and not self.filename:
            self.filename = self.image.name.rsplit("/", 1)[-1][:220]
        if self.image and not self.file_size:
            try:
                self.file_size = self.image.size
            except Exception:  # noqa: BLE001 - storage may not expose size yet
                self.file_size = 0
        super().save(*args, **kwargs)
        if self.image and not self.width:
            width, height = read_image_dimensions(self.image)
            if width:
                GalleryImage.objects.filter(pk=self.pk).update(width=width, height=height)
                self.width, self.height = width, height

    @property
    def display_title(self):
        return self.title or self.filename or f"Frame {self.order + 1}"

    @property
    def display_alt(self):
        return self.alt_text or self.display_title

    @property
    def orientation(self):
        if not self.width or not self.height:
            return "landscape"
        return "portrait" if self.height > self.width else "landscape"

    def get_download_url(self):
        return reverse("client:image_download", args=[self.gallery.slug, str(self.uuid)])


class DownloadHistory(UUIDModel, TimeStampedModel):
    class Kind(models.TextChoices):
        SINGLE = "single", "Single image"
        BULK = "bulk", "Bulk archive"

    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name="downloads")
    image = models.ForeignKey(
        GalleryImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="downloads",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="downloads",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="downloads",
    )
    download_type = models.CharField(max_length=12, choices=Kind.choices, default=Kind.SINGLE)
    item_count = models.PositiveIntegerField(default=1)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=400, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "download history"
        indexes = [models.Index(fields=["gallery", "-created_at"])]

    def __str__(self):
        return f"{self.get_download_type_display()} - {self.gallery.title}"


class GalleryAccessLog(UUIDModel, TimeStampedModel):
    class Action(models.TextChoices):
        VIEW = "view", "Viewed gallery"
        UNLOCK_OK = "unlock_ok", "Unlocked with code"
        UNLOCK_FAIL = "unlock_fail", "Wrong access code"
        DOWNLOAD = "download", "Downloaded"
        SELECT = "select", "Changed selection"
        SUBMIT = "submit", "Submitted selection"
        DENIED = "denied", "Access denied"
        EXPIRED = "expired", "Expired gallery"

    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name="access_logs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_access_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices, default=Action.VIEW, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=400, blank=True)
    path = models.CharField(max_length=300, blank=True)
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["gallery", "-created_at"])]

    def __str__(self):
        return f"{self.get_action_display()} - {self.gallery_id}"