"""Client-facing gallery area: browse, select, submit, download."""

import json

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.albums.models import AlbumRequest, AlbumSelection
from apps.common.mixins import ClientRequiredMixin, PageMetaMixin
from apps.notifications.models import Notification

from .forms import GalleryAccessForm, SelectionSubmitForm
from .models import Gallery, GalleryImage
from .services import (
    build_gallery_zip,
    gallery_unlocked,
    log_access,
    record_download,
    unlock_gallery_in_session,
)


class GalleryAccessMixin:
    """Resolves a gallery and enforces login / share-code / expiry rules."""

    def get_gallery(self):
        gallery = get_object_or_404(
            Gallery.objects.select_related("customer", "photographer", "category"),
            slug=self.kwargs["slug"],
        )
        return gallery

    def check_access(self, gallery):
        """Return None when allowed, otherwise an HttpResponse to return."""
        request = self.request
        user = request.user

        if user.is_authenticated and user.has_studio_access:
            return None

        if gallery.status == Gallery.Status.DRAFT:
            log_access(gallery, request, action="denied", note="draft gallery")
            raise Http404("Gallery not available.")

        if gallery.is_expired:
            log_access(gallery, request, action="expired")
            return render(
                request,
                "client/gallery_expired.html",
                {"gallery": gallery, "page_title": "Gallery expired"},
                status=410,
            )

        if gallery.visibility == Gallery.Visibility.PUBLIC:
            return None

        if gallery.can_be_viewed_by(user):
            return None

        if gallery.visibility == Gallery.Visibility.CODE:
            if gallery_unlocked(request, gallery):
                return None
            return redirect("client:gallery_share", token=str(gallery.uuid))

        log_access(gallery, request, action="denied", note="not the gallery owner")
        return redirect(f"{reverse('accounts:client_login')}?next={request.get_full_path()}")

    def resolve_customer(self, gallery):
        """The customer a selection should be attributed to."""
        user = self.request.user
        if user.is_authenticated:
            profile = getattr(user, "customer_profile", None)
            if profile is not None and profile.pk == gallery.customer_id:
                return profile
        if gallery_unlocked(self.request, gallery) or gallery.visibility == Gallery.Visibility.PUBLIC:
            return gallery.customer
        if user.is_authenticated and user.has_studio_access:
            return gallery.customer
        return None


class ClientIndexView(ClientRequiredMixin, PageMetaMixin, ListView):
    """Landing page of the client area - every gallery assigned to the client."""

    template_name = "client/index.html"
    context_object_name = "galleries"
    page_title = "Your galleries"

    def get_queryset(self):
        customer = getattr(self.request.user, "customer_profile", None)
        queryset = Gallery.objects.select_related("photographer", "category").annotate(
            photo_count=Count("images", filter=Q(images__is_hidden=False), distinct=True),
            picks=Count("selections", filter=Q(selections__is_selected=True), distinct=True),
        )
        if customer is None:
            if self.request.user.has_studio_access:
                return queryset.exclude(status=Gallery.Status.DRAFT).order_by("-created_at")[:24]
            return queryset.none()
        return queryset.filter(customer=customer).exclude(status=Gallery.Status.DRAFT).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = getattr(self.request.user, "customer_profile", None)
        context["customer"] = customer
        context["album_requests"] = (
            AlbumRequest.objects.filter(customer=customer).select_related("gallery")[:5]
            if customer
            else []
        )
        context["notifications"] = Notification.objects.for_user(self.request.user)[:6]
        return context


class GalleryShareView(PageMetaMixin, FormView):
    """Access-code gate for galleries shared by link."""

    template_name = "client/gallery_access.html"
    form_class = GalleryAccessForm
    page_title = "Private gallery"

    def dispatch(self, request, *args, **kwargs):
        self.gallery = get_object_or_404(Gallery, uuid=kwargs["token"])
        if self.gallery.visibility == Gallery.Visibility.PRIVATE:
            return redirect(f"{reverse('accounts:client_login')}?next={self.gallery.get_absolute_url()}")
        if self.gallery.is_expired:
            return render(
                request,
                "client/gallery_expired.html",
                {"gallery": self.gallery, "page_title": "Gallery expired"},
                status=410,
            )
        if gallery_unlocked(request, self.gallery) or self.gallery.visibility == Gallery.Visibility.PUBLIC:
            return redirect(self.gallery.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["gallery"] = self.gallery
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gallery"] = self.gallery
        return context

    def form_valid(self, form):
        unlock_gallery_in_session(self.request, self.gallery)
        log_access(self.gallery, self.request, action="unlock_ok")
        messages.success(self.request, "Welcome - your gallery is unlocked.")
        return redirect(self.gallery.get_absolute_url())

    def form_invalid(self, form):
        log_access(self.gallery, self.request, action="unlock_fail")
        return super().form_invalid(form)


class GalleryDetailView(GalleryAccessMixin, PageMetaMixin, DetailView):
    template_name = "client/gallery_detail.html"
    context_object_name = "gallery"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_gallery()
        denial = self.check_access(self.object)
        if denial is not None:
            return denial
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.object

    def get(self, request, *args, **kwargs):
        self.object.register_view()
        log_access(self.object, request, action="view")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gallery = self.object
        customer = self.resolve_customer(gallery)
        images = gallery.images.filter(is_hidden=False).order_by("order", "id")

        selected_ids = set()
        if customer is not None:
            selected_ids = set(
                AlbumSelection.objects.filter(
                    gallery=gallery, customer=customer, is_selected=True
                ).values_list("image_id", flat=True)
            )

        latest_request = (
            AlbumRequest.objects.filter(gallery=gallery, customer=customer).first()
            if customer
            else None
        )

        context.update(
            {
                "images": images,
                "image_total": images.count(),
                "selected_ids": selected_ids,
                "selected_count": len(selected_ids),
                "customer": customer,
                "can_select": gallery.selection_open and customer is not None,
                "can_download": gallery.allow_downloads and not gallery.is_expired,
                "submit_form": SelectionSubmitForm(),
                "latest_request": latest_request,
                "page_title": gallery.title,
                "selection_limit": gallery.selection_limit,
            }
        )
        return context


@method_decorator(require_POST, name="dispatch")
class ToggleSelectionView(GalleryAccessMixin, View):
    """AJAX endpoint that flips a single image in/out of the client's picks."""

    def post(self, request, *args, **kwargs):
        gallery = self.get_gallery()
        denial = self.check_access(gallery)
        if denial is not None:
            return JsonResponse({"ok": False, "error": "Access denied."}, status=403)

        customer = self.resolve_customer(gallery)
        if customer is None:
            return JsonResponse({"ok": False, "error": "Sign in to select photographs."}, status=403)
        if not gallery.selection_open:
            return JsonResponse({"ok": False, "error": "Selection is closed for this gallery."}, status=400)

        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            payload = {}
        image_uuid = payload.get("image") or request.POST.get("image")
        if not image_uuid:
            return JsonResponse({"ok": False, "error": "Missing image reference."}, status=400)

        try:
            image = gallery.images.get(uuid=image_uuid)
        except (GalleryImage.DoesNotExist, ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Unknown image."}, status=404)

        selection, created = AlbumSelection.objects.get_or_create(
            gallery=gallery,
            image=image,
            customer=customer,
            defaults={"is_selected": True, "sequence": gallery.selections.count()},
        )
        if not created:
            selection.is_selected = not selection.is_selected
            selection.save(update_fields=["is_selected", "updated_at"])

        selected_count = AlbumSelection.objects.filter(
            gallery=gallery, customer=customer, is_selected=True
        ).count()

        limit = gallery.selection_limit
        if limit and selection.is_selected and selected_count > limit:
            selection.is_selected = False
            selection.save(update_fields=["is_selected", "updated_at"])
            return JsonResponse(
                {
                    "ok": False,
                    "error": f"You can select up to {limit} photographs.",
                    "selected": False,
                    "count": selected_count - 1,
                },
                status=400,
            )

        log_access(
            gallery,
            request,
            action="select",
            note=f"{'selected' if selection.is_selected else 'removed'} {image.display_title}",
        )
        return JsonResponse(
            {
                "ok": True,
                "selected": selection.is_selected,
                "count": selected_count,
                "limit": limit,
            }
        )


class SubmitSelectionView(GalleryAccessMixin, View):
    """Turns the current picks into a submitted album request."""

    def post(self, request, *args, **kwargs):
        gallery = self.get_gallery()
        denial = self.check_access(gallery)
        if denial is not None:
            return denial

        customer = self.resolve_customer(gallery)
        if customer is None:
            messages.error(request, "Sign in to submit your selection.")
            return redirect("accounts:client_login")

        selections = AlbumSelection.objects.filter(gallery=gallery, customer=customer, is_selected=True)
        if not selections.exists():
            messages.warning(request, "Select at least one photograph before submitting.")
            return redirect(gallery.get_absolute_url())

        form = SelectionSubmitForm(request.POST)
        album_type = "fine_art"
        notes = ""
        if form.is_valid():
            album_type = form.cleaned_data.get("album_type") or "fine_art"
            notes = form.cleaned_data.get("notes") or ""

        album_request = self._get_or_create_request(gallery, customer, album_type, notes)

        selections.update(album_request=album_request, updated_at=timezone.now())
        album_request.mark_submitted()

        log_access(gallery, request, action="submit", note=f"{selections.count()} photos")
        messages.success(
            request,
            f"Your selection of {selections.count()} photographs has been sent to the studio.",
        )
        return redirect(gallery.get_absolute_url())

    @staticmethod
    def _get_or_create_request(gallery, customer, album_type, notes):
        existing = AlbumRequest.objects.filter(
            gallery=gallery,
            customer=customer,
            status__in=[AlbumRequest.Status.DRAFT, AlbumRequest.Status.SUBMITTED],
        ).first()
        if existing:
            existing.album_type = album_type or existing.album_type
            if notes:
                existing.notes = notes
            existing.save(update_fields=["album_type", "notes", "updated_at"])
            return existing
        return AlbumRequest.objects.create(
            gallery=gallery,
            customer=customer,
            title=f"{gallery.title} - album selection",
            album_type=album_type,
            notes=notes,
        )


class ImageDownloadView(GalleryAccessMixin, View):
    """Permission-checked, logged delivery of a single original file."""

    def get(self, request, *args, **kwargs):
        gallery = self.get_gallery()
        denial = self.check_access(gallery)
        if denial is not None:
            return denial

        if not gallery.allow_downloads:
            messages.error(request, "Downloads are disabled for this gallery.")
            return redirect(gallery.get_absolute_url())

        image = get_object_or_404(gallery.images, uuid=kwargs["image_uuid"])
        if not image.allow_download or image.is_hidden:
            raise Http404("This file is not available for download.")

        record_download(gallery, request=request, image=image, kind="single", item_count=1)

        try:
            handle = image.image.open("rb")
        except Exception as exc:  # noqa: BLE001
            raise Http404("The original file could not be read.") from exc

        filename = image.filename or image.image.name.rsplit("/", 1)[-1]
        response = FileResponse(handle, as_attachment=True, filename=filename)
        response["X-Content-Type-Options"] = "nosniff"
        return response


class GalleryDownloadAllView(GalleryAccessMixin, View):
    """Streams a ZIP of every downloadable image in the gallery."""

    def get(self, request, *args, **kwargs):
        gallery = self.get_gallery()
        denial = self.check_access(gallery)
        if denial is not None:
            return denial

        if not (gallery.allow_downloads and gallery.allow_bulk_download):
            messages.error(request, "Bulk download is disabled for this gallery.")
            return redirect(gallery.get_absolute_url())

        only_selected = request.GET.get("selection") == "1"
        images = gallery.images.filter(is_hidden=False, allow_download=True)
        if only_selected:
            customer = self.resolve_customer(gallery)
            selected_ids = AlbumSelection.objects.filter(
                gallery=gallery, customer=customer, is_selected=True
            ).values_list("image_id", flat=True)
            images = images.filter(pk__in=list(selected_ids))

        if not images.exists():
            messages.warning(request, "There is nothing to download yet.")
            return redirect(gallery.get_absolute_url())

        buffer, included = build_gallery_zip(gallery, images=images)
        record_download(gallery, request=request, kind="bulk", item_count=included)

        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        suffix = "-selection" if only_selected else ""
        response["Content-Disposition"] = f'attachment; filename="{gallery.slug}{suffix}.zip"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ClientNotificationsView(ClientRequiredMixin, PageMetaMixin, ListView):
    template_name = "client/notifications.html"
    context_object_name = "notifications"
    paginate_by = 20
    page_title = "Notifications"

    def get_queryset(self):
        return Notification.objects.for_user(self.request.user)

    def post(self, request, *args, **kwargs):
        Notification.objects.for_user(request.user).unread().update(
            is_read=True, read_at=timezone.now()
        )
        messages.success(request, "All notifications marked as read.")
        return redirect("client:notifications")


class ClientHelpView(ClientRequiredMixin, PageMetaMixin, TemplateView):
    template_name = "client/help.html"
    page_title = "Gallery help"