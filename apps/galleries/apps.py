from django.apps import AppConfig


class GalleriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.galleries"
    label = "galleries"
    verbose_name = "Galleries"

    def ready(self):
        from . import signals  # noqa: F401