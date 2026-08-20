from django.apps import AppConfig


class AlbumsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.albums"
    label = "albums"
    verbose_name = "Albums & selections"

    def ready(self):
        from . import signals  # noqa: F401