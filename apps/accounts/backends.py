from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """Allow signing in with either the username or the email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = (username or kwargs.get("email") or "").strip()
        if not identifier or password is None:
            return None
        try:
            user = User.objects.get(Q(username__iexact=identifier) | Q(email__iexact=identifier))
        except User.DoesNotExist:
            # Run the default hasher once to equalise timing between
            # "no such user" and "wrong password".
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            user = (
                User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier))
                .order_by("id")
                .first()
            )
            if user is None:
                return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None