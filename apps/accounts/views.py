"""Authentication views for clients and studio staff."""

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from apps.common.mixins import PageMetaMixin

from .forms import (
    ProfileForm,
    StudioAuthenticationForm,
    StyledAuthenticationForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)


class BaseLoginView(PageMetaMixin, auth_views.LoginView):
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember = form.cleaned_data.get("remember_me")
        response = super().form_valid(form)
        if not remember:
            self.request.session.set_expiry(0)
        return response

    def form_invalid(self, form):
        messages.error(self.request, "We couldn't sign you in. Check your details and try again.")
        return super().form_invalid(form)


class ClientLoginView(BaseLoginView):
    """Sign-in for studio clients."""

    template_name = "accounts/client_login.html"
    authentication_form = StyledAuthenticationForm
    page_title = "Client area"
    meta_description = "Sign in to your private MS Photo Studio gallery."

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        if self.request.user.has_studio_access:
            return reverse_lazy("dashboard:index")
        return reverse_lazy("client:index")


class StudioLoginView(BaseLoginView):
    """Sign-in for the studio dashboard."""

    template_name = "accounts/admin_login.html"
    authentication_form = StudioAuthenticationForm
    page_title = "Studio access"

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("dashboard:index")


class StudioLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("website:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You have been signed out.")
        return super().dispatch(request, *args, **kwargs)


class PasswordResetView(PageMetaMixin, auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")
    page_title = "Reset your password"


class PasswordResetDoneView(PageMetaMixin, auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"
    page_title = "Check your inbox"


class PasswordResetConfirmView(PageMetaMixin, auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")
    page_title = "Choose a new password"


class PasswordResetCompleteView(PageMetaMixin, auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
    page_title = "Password updated"


class PasswordChangeView(PageMetaMixin, auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")
    page_title = "Change password"

    def form_valid(self, form):
        messages.success(self.request, "Your password has been updated.")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, PageMetaMixin, UpdateView):
    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")
    page_title = "Your profile"

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile saved.")
        return super().form_valid(form)