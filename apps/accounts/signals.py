from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from apps.common.utils import get_client_ip, get_user_agent


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    from apps.analytics.models import ActivityLog

    ip = get_client_ip(request)
    user.register_login(ip=ip)
    ActivityLog.log(
        actor=user,
        action=ActivityLog.Actions.LOGIN,
        description=f"{user.get_display_name()} signed in.",
        target=user,
        request=request,
    )


@receiver(user_login_failed)
def handle_user_login_failed(sender, credentials, request=None, **kwargs):
    from apps.analytics.models import ActivityLog

    identifier = credentials.get("username") or credentials.get("email") or "unknown"
    ActivityLog.objects.create(
        action=ActivityLog.Actions.LOGIN_FAILED,
        description=f"Failed sign-in attempt for '{identifier}'.",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        metadata={"identifier": str(identifier)[:120]},
    )