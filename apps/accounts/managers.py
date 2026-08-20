from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the custom `User` model (username + email)."""

    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("A username is required.")
        email = self.normalize_email(email) if email else ""
        username = username.strip().lower()
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_client(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", self.model.Roles.CLIENT)
        return self.create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Roles.ADMIN)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(username, email, password, **extra_fields)

    def studio_team(self):
        return self.filter(
            role__in=[self.model.Roles.ADMIN, self.model.Roles.PHOTOGRAPHER, self.model.Roles.STAFF],
            is_active=True,
        )