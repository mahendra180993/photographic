from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AlbumRequest


@receiver(post_save, sender=AlbumRequest)
def album_request_saved(sender, instance, created, **kwargs):
    from apps.notifications.services import notify_customer, notify_studio_team

    if instance.status == AlbumRequest.Status.SUBMITTED and instance.submitted_at:
        # Only fire once per transition into "submitted".
        if getattr(instance, "_selection_notified", False):
            return
        instance._selection_notified = True
        notify_studio_team(
            title="Client submitted a selection",
            message=(
                f"{instance.customer.full_name} submitted {instance.selection_count} "
                f"photos from '{instance.gallery.title}'."
            ),
            category="selection",
            level="success",
            url=instance.get_absolute_url(),
            gallery=instance.gallery,
            email_subject=f"[Lumina Atelier] Selection submitted by {instance.customer.full_name}",
        )
        notify_customer(
            customer=instance.customer,
            title="Selection received",
            message=(
                f"Thank you - we received your {instance.selection_count} picks for "
                f"'{instance.gallery.title}'. Our team will be in touch shortly."
            ),
            category="selection",
            level="success",
            url=instance.gallery.get_absolute_url(),
            gallery=instance.gallery,
            email_subject="[Lumina Atelier] We received your selection",
        )