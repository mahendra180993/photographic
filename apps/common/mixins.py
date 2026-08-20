"""Access-control mixins used by the client area and the studio dashboard."""

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse


class StaffRequiredMixin(AccessMixin):
    """Only studio staff (admin / photographer / staff roles) may pass."""

    permission_denied_message = "You need studio access to open that page."

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(f"{reverse('accounts:admin_login')}?next={request.get_full_path()}")
        if not user.has_studio_access:
            messages.error(request, self.permission_denied_message)
            return redirect("website:home")
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(StaffRequiredMixin):
    """Reserved for owner/admin-only screens (settings, deletions)."""

    permission_denied_message = "Only studio administrators can open that page."

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and user.has_studio_access and not user.is_studio_admin:
            messages.error(request, self.permission_denied_message)
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin(AccessMixin):
    """Logged-in customers (staff may preview too)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:client_login')}?next={request.get_full_path()}")
        if not (request.user.is_client or request.user.has_studio_access):
            messages.error(request, "This area is reserved for studio clients.")
            return redirect("website:home")
        return super().dispatch(request, *args, **kwargs)


class PageMetaMixin:
    """Injects page title / meta description into the template context."""

    page_title = ""
    page_subtitle = ""
    meta_description = ""
    active_nav = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", self.page_title)
        context.setdefault("page_subtitle", self.page_subtitle)
        context.setdefault("meta_description", self.meta_description)
        context.setdefault("active_nav", self.active_nav)
        return context


class SuccessMessageMixin:
    """Lightweight replacement that also works on DeleteView."""

    success_message = ""

    def get_success_message(self, obj=None):
        if not self.success_message:
            return ""
        try:
            return self.success_message.format(object=obj)
        except (KeyError, IndexError):
            return self.success_message

    def form_valid(self, form):
        response = super().form_valid(form)
        message = self.get_success_message(getattr(self, "object", None))
        if message:
            messages.success(self.request, message)
        return response