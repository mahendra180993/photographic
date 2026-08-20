"""In-app notifications for studio staff and clients."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel


class NotificationQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(is_read=False)

    def for_user(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(recipient=user)


class Notification(UUIDModel, TimeStampedModel):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class Category(models.TextChoices):
        GALLERY = "gallery", "Gallery"
        SELECTION = "selection", "Selection"
        ALBUM = "album", "Album"
        CONTACT = "contact", "Enquiry"
        ACCOUNT = "account", "Account"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    level = models.CharField(max_length=12, choices=Level.choices, default=Level.INFO)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.SYSTEM, db_index=True)
    url = models.CharField(max_length=400, blank=True)

    related_gallery = models.ForeignKey(
        "galleries.Gallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(blank=True, null=True)
    emailed = models.BooleanField(default=False)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])
        return self

    @property
    def icon(self):
        return {
            self.Category.GALLERY: "image",
            self.Category.SELECTION: "check",
            self.Category.ALBUM: "book",
            self.Category.CONTACT: "mail",
            self.Category.ACCOUNT: "user",
            self.Category.SYSTEM: "bell",
        }.get(self.category, "bell")