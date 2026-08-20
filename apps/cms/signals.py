from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ContactMessage


@receiver(post_save, sender=ContactMessage)
def notify_studio_of_contact_message(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.notifications.services import notify_studio_team

    notify_studio_team(
        title="New enquiry received",
        message=f"{instance.name} sent a message: {instance.display_subject}",
        category="contact",
        level="info",
        url=f"/studio/messages/{instance.pk}/",
        email_subject=f"[MS Photo Studio] New enquiry from {instance.name}",
    )