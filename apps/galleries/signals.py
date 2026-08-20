from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Gallery


@receiver(pre_save, sender=Gallery)
def remember_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    previous = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    instance._previous_status = previous


@receiver(post_save, sender=Gallery)
def gallery_saved(sender, instance, created, **kwargs):
    from apps.notifications.services import notify_customer, notify_studio_team

    previous = getattr(instance, "_previous_status", None)

    if created:
        notify_studio_team(
            title="Gallery created",
            message=f"'{instance.title}' was created for {instance.customer.full_name}.",
            category="gallery",
            level="info",
            url=instance.get_dashboard_url(),
            gallery=instance,
        )
        return

    became_live = previous != instance.status and instance.status in {
        Gallery.Status.READY,
        Gallery.Status.DELIVERED,
    }
    if became_live and instance.notify_customer:
        notify_customer(
            customer=instance.customer,
            title="Your gallery is ready",
            message=(
                f"'{instance.title}' is now available in your private client area. "
                "Sign in to view, select and download your photographs."
            ),
            category="gallery",
            level="success",
            url=instance.get_absolute_url(),
            gallery=instance,
            email_subject=f"[Lumina Atelier] Your gallery '{instance.title}' is ready",
        )
        Gallery.objects.filter(pk=instance.pk).update(notified_at=timezone.now())