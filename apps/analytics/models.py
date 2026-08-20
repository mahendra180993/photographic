"""Lightweight audit trail powering the dashboard activity feed."""

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel
from apps.common.utils import get_client_ip, get_user_agent


class ActivityLog(UUIDModel, TimeStampedModel):
    class Actions(models.TextChoices):
        LOGIN = "login", "Signed in"
        LOGIN_FAILED = "login_failed", "Sign-in failed"
        LOGOUT = "logout", "Signed out"
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        DELETE = "delete", "Deleted"
        UPLOAD = "upload", "Uploaded images"
        DOWNLOAD = "download", "Downloaded"
        SELECTION = "selection", "Selection changed"
        SUBMIT = "submit", "Selection submitted"
        MESSAGE = "message", "Enquiry received"
        SETTINGS = "settings", "Settings changed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=24, choices=Actions.choices, default=Actions.UPDATE, db_index=True)
    description = models.CharField(max_length=300, blank=True)
    target_type = models.CharField(max_length=80, blank=True, db_index=True)
    target_id = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=400, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "activity log"
        verbose_name_plural = "activity log"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.description[:60]}"

    @classmethod
    def log(cls, actor=None, action="update", description="", target=None, request=None, **metadata):
        target_type = target.__class__.__name__ if target is not None else ""
        target_id = str(getattr(target, "pk", "")) if target is not None else ""
        return cls.objects.create(
            actor=actor if (actor and getattr(actor, "pk", None)) else None,
            action=action,
            description=description[:300],
            target_type=target_type,
            target_id=target_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            metadata=metadata or {},
        )

    @property
    def icon(self):
        return {
            "login": "log-in",
            "upload": "upload",
            "download": "download",
            "create": "plus",
            "delete": "trash",
            "submit": "check-circle",
            "message": "mail",
        }.get(self.action, "activity")