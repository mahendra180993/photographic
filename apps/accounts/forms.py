"""Auth + profile forms with consistent styling."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)

User = get_user_model()

INPUT_CLASS = (
    "w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-paper "
    "placeholder-paper/40 outline-none transition focus:border-gold focus:ring-2 focus:ring-gold/25"
)


def style(field, placeholder=None, autocomplete=None):
    field.widget.attrs.setdefault("class", INPUT_CLASS)
    if placeholder:
        field.widget.attrs.setdefault("placeholder", placeholder)
    if autocomplete:
        field.widget.attrs.setdefault("autocomplete", autocomplete)
    return field


class StyledAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=True, label="Keep me signed in")

    error_messages = {
        "invalid_login": "Those credentials did not match our records. Please try again.",
        "inactive": "This account has been deactivated. Contact the studio for help.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email or username"
        style(self.fields["username"], "you@example.com", "username")
        style(self.fields["password"], "Your password", "current-password")
        self.fields["remember_me"].widget.attrs.update(
            {"class": "h-4 w-4 rounded border-black/20 text-gold focus:ring-gold"}
        )


class StudioAuthenticationForm(StyledAuthenticationForm):
    """Login form for the studio dashboard - rejects client accounts."""

    error_messages = {
        **StyledAuthenticationForm.error_messages,
        "no_studio_access": "This account does not have studio access.",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.has_studio_access:
            raise forms.ValidationError(self.error_messages["no_studio_access"], code="no_studio_access")


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style(self.fields["email"], "you@example.com", "email")


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("new_password1", "new_password2"):
            style(self.fields[name], "New password", "new-password")


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("old_password", "new_password1", "new_password2"):
            style(self.fields[name])


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "avatar", "timezone_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "avatar":
                field.widget.attrs.setdefault("class", "block w-full text-sm text-ink/70")
            else:
                style(field)


class StaffUserForm(forms.ModelForm):
    """Create / edit studio team logins from the dashboard."""

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "autocomplete": "new-password"}),
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "role", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class", "h-4 w-4 rounded border-black/20 text-gold focus:ring-gold"
                )
            else:
                style(field)

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()
        user.is_staff = user.role in {User.Roles.ADMIN, User.Roles.STAFF, User.Roles.PHOTOGRAPHER}
        if commit:
            user.save()
        return user