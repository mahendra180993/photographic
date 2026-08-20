"""Creation + email fan-out for notifications (email is a safe stub in dev)."""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger("lumina.notifications")


def _send_email(subject, body, recipients):
    recipients = [address for address in recipients if address]
    if not recipients:
        return False
    if not getattr(settings, "NOTIFY_EMAILS_ENABLED", True):
        logger.info("Email disabled, skipped: %s -> %s", subject, recipients)
        return False
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True,
        )
        return True
    except Exception as exc:  # noqa: BLE001 - notifications must never break a request
        logger.warning("Notification email failed (%s): %s", subject, exc)
        return False


def create_notification(recipient, title, message="", category="system", level="info",
                        url="", gallery=None, actor=None, emailed=False):
    if recipient is None:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        title=title[:200],
        message=message,
        category=category,
        level=level,
        url=url[:400],
        related_gallery=gallery,
        emailed=emailed,
    )


def notify_studio_team(title, message="", category="system", level="info", url="",
                       gallery=None, actor=None, email_subject=None):
    """Notify every active studio member in-app, plus one summary email."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    recipients = list(User.objects.studio_team())
    emailed = _send_email(
        email_subject or f"[MS Photo Studio] {title}",
        message,
        [settings.STUDIO_NOTIFICATION_EMAIL],
    ) if email_subject else False

    created = []
    for user in recipients:
        created.append(
            create_notification(
                recipient=user,
                title=title,
                message=message,
                category=category,
                level=level,
                url=url,
                gallery=gallery,
                actor=actor,
                emailed=emailed,
            )
        )
    logger.info("Studio notified: %s (%s recipients)", title, len(created))
    return created


def notify_customer(customer, title, message="", category="gallery", level="info", url="",
                    gallery=None, actor=None, email_subject=None):
    """Notify a customer in-app (if they have a login) and by email."""
    emailed = False
    if email_subject:
        full_url = f"{settings.SITE_DOMAIN}{url}" if url.startswith("/") else url
        body = f"{message}\n\n{full_url}\n\n-- {settings.STUDIO_BRAND_NAME}"
        emailed = _send_email(email_subject, body, [customer.email])

    notification = None
    if customer.user_id:
        notification = create_notification(
            recipient=customer.user,
            title=title,
            message=message,
            category=category,
            level=level,
            url=url,
            gallery=gallery,
            actor=actor,
            emailed=emailed,
        )
    logger.info("Customer notified: %s -> %s", title, customer.email)
    return notification