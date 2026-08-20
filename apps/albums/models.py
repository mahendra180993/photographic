"""Client photo selections and the album orders they roll up into."""

from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel


class AlbumRequest(UUIDModel, TimeStampedModel):
    """The envelope a client submits: 'these are my picks, make my album'."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In review"
        APPROVED = "approved", "Approved"
        IN_PRODUCTION = "in_production", "In production"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class AlbumType(models.TextChoices):
        FINE_ART = "fine_art", "Fine art album"
        LAYFLAT = "layflat", "Layflat album"
        STORYBOOK = "storybook", "Storybook"
        PRINT_BOX = "print_box", "Print box"
        DIGITAL = "digital", "Digital delivery only"

    gallery = models.ForeignKey(
        "galleries.Gallery",
        on_delete=models.CASCADE,
        related_name="album_requests",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="album_requests",
    )
    title = models.CharField(max_length=200, blank=True)
    album_type = models.CharField(max_length=20, choices=AlbumType.choices, default=AlbumType.FINE_ART)
    size = models.CharField(max_length=60, blank=True, default="30x30 cm")
    cover_material = models.CharField(max_length=80, blank=True, default="Linen")
    page_count = models.PositiveIntegerField(default=30)
    notes = models.TextField(blank=True, help_text="Client instructions for the studio.")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return self.title or f"Album request for {self.gallery.title}"

    def get_absolute_url(self):
        return reverse("dashboard:album_detail", args=[self.pk])

    @property
    def selection_count(self):
        return self.selections.filter(is_selected=True).count()

    @property
    def is_editable_by_client(self):
        return self.status in {self.Status.DRAFT, self.Status.SUBMITTED}

    def mark_submitted(self, commit=True):
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        if not self.title:
            self.title = f"{self.gallery.title} - album selection"
        if commit:
            self.save(update_fields=["status", "submitted_at", "title", "updated_at"])
        return self


class AlbumSelection(UUIDModel, TimeStampedModel):
    """One image chosen by a client inside a gallery."""

    gallery = models.ForeignKey(
        "galleries.Gallery",
        on_delete=models.CASCADE,
        related_name="selections",
    )
    image = models.ForeignKey(
        "galleries.GalleryImage",
        on_delete=models.CASCADE,
        related_name="selections",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="selections",
    )
    album_request = models.ForeignKey(
        AlbumRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selections",
    )
    is_selected = models.BooleanField(default=True, db_index=True)
    is_favorite = models.BooleanField(default=False)
    sequence = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("sequence", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["gallery", "image", "customer"],
                name="unique_selection_per_customer_image",
            )
        ]
        indexes = [models.Index(fields=["gallery", "is_selected"])]

    def __str__(self):
        state = "selected" if self.is_selected else "deselected"
        return f"{self.image.display_title} ({state})"