"""Custom user model for the studio platform."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel
from apps.common.utils import avatar_path

from .managers import UserManager

username_validator = RegexValidator(
    r"^[\w.@+-]+$",
    "Use letters, digits and @/./+/-/_ only.",
)


class User(AbstractBaseUser, PermissionsMixin, UUIDModel, TimeStampedModel):
    """Single user table for studio staff and clients, separated by `role`."""

    class Roles(models.TextChoices):
        ADMIN = "admin", "Studio Admin"
        PHOTOGRAPHER = "photographer", "Photographer"
        STAFF = "staff", "Studio Staff"
        CLIENT = "client", "Client"

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[username_validator],
        help_text="Used to sign in. Clients may also sign in with their email.",
    )
    email = models.EmailField("email address", max_length=254, blank=True, db_index=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CLIENT, db_index=True)
    avatar = models.ImageField(upload_to=avatar_path, blank=True, null=True)

    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Django-level staff flag. Studio access is driven by `role`.",
    )
    email_verified = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    login_count = models.PositiveIntegerField(default=0)
    timezone_name = models.CharField(max_length=64, blank=True, default="UTC")
    notes = models.TextField(blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.get_display_name()

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.strip().lower()
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    # -- naming ---------------------------------------------------------
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.username

    def get_display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        full = self.get_full_name()
        if full:
            parts = full.split()
            return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()
        return self.username[:2].upper()

    # -- roles ----------------------------------------------------------
    @property
    def is_client(self):
        return self.role == self.Roles.CLIENT

    @property
    def is_photographer(self):
        return self.role == self.Roles.PHOTOGRAPHER

    @property
    def is_studio_admin(self):
        return self.role == self.Roles.ADMIN or self.is_superuser

    @property
    def has_studio_access(self):
        return self.is_superuser or self.role in {
            self.Roles.ADMIN,
            self.Roles.PHOTOGRAPHER,
            self.Roles.STAFF,
        }

    @property
    def role_label(self):
        return self.get_role_display()

    # -- helpers --------------------------------------------------------
    def touch_activity(self, commit=True):
        self.last_activity_at = timezone.now()
        if commit:
            User.objects.filter(pk=self.pk).update(last_activity_at=self.last_activity_at)

    def register_login(self, ip=None):
        self.login_count = (self.login_count or 0) + 1
        self.last_login_ip = ip
        self.last_activity_at = timezone.now()
        self.save(update_fields=["login_count", "last_login_ip", "last_activity_at", "updated_at"])

    @property
    def customer_record(self):
        return getattr(self, "customer_profile", None)

    @property
    def photographer_record(self):
        return getattr(self, "photographer_profile", None)