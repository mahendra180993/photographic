"""Custom studio dashboard - a full admin UI built on class-based views."""

import json
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.albums.models import AlbumRequest, AlbumSelection
from apps.analytics.models import ActivityLog
from apps.cms.models import FAQ, ContactMessage, SEOSettings, TeamMember, Testimonial, WebsiteSettings
from apps.common.mixins import AdminRequiredMixin, PageMetaMixin, StaffRequiredMixin
from apps.customers.models import Customer, Photographer
from apps.galleries.models import DownloadHistory, Gallery, GalleryAccessLog, GalleryCategory, GalleryImage
from apps.notifications.models import Notification
from apps.portfolio.models import PortfolioCategory, PortfolioImage
from apps.services.models import Service

from . import forms as dash_forms


def log_action(request, action, description, target=None, **metadata):
    return ActivityLog.log(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        description=description,
        target=target,
        request=request,
        **metadata,
    )


# ---------------------------------------------------------------------------
# Reusable CRUD scaffolding
# ---------------------------------------------------------------------------
class DashboardListView(StaffRequiredMixin, PageMetaMixin, ListView):
    template_name = "dashboard/generic_list.html"
    paginate_by = 20
    columns = []
    search_fields = []
    create_url = None
    create_label = "Add new"
    edit_url = None
    delete_url = None
    detail_url = None
    empty_message = "Nothing here yet."

    def get_queryset(self):
        queryset = super().get_queryset()
        term = (self.request.GET.get("q") or "").strip()
        if term and self.search_fields:
            lookup = Q()
            for field in self.search_fields:
                lookup |= Q(**{f"{field}__icontains": term})
            queryset = queryset.filter(lookup)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "columns": self.columns,
                "create_url": reverse(self.create_url) if self.create_url else None,
                "create_label": self.create_label,
                "edit_url_name": self.edit_url,
                "delete_url_name": self.delete_url,
                "detail_url_name": self.detail_url,
                "search_term": self.request.GET.get("q", ""),
                "searchable": bool(self.search_fields),
                "empty_message": self.empty_message,
                "total_count": self.get_queryset().count(),
            }
        )
        return context


class DashboardFormViewMixin(StaffRequiredMixin, PageMetaMixin):
    template_name = "dashboard/generic_form.html"
    cancel_url = None
    success_message = "Saved."
    form_intro = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse(self.cancel_url) if self.cancel_url else None
        context["form_intro"] = self.form_intro
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        log_action(
            self.request,
            ActivityLog.Actions.CREATE if isinstance(self, CreateView) else ActivityLog.Actions.UPDATE,
            f"{self.success_message} ({self.object})",
            target=self.object,
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class DashboardCreateView(DashboardFormViewMixin, CreateView):
    success_message = "Created successfully."


class DashboardUpdateView(DashboardFormViewMixin, UpdateView):
    success_message = "Changes saved."


class DashboardDeleteView(StaffRequiredMixin, PageMetaMixin, DeleteView):
    template_name = "dashboard/generic_confirm_delete.html"
    success_message = "Deleted."

    def form_valid(self, form):
        obj = self.get_object()
        log_action(self.request, ActivityLog.Actions.DELETE, f"Deleted {obj}", target=obj)
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class DashboardSingletonUpdateView(AdminRequiredMixin, PageMetaMixin, UpdateView):
    template_name = "dashboard/settings_form.html"
    success_message = "Settings updated."

    def get_object(self, queryset=None):
        return self.model.load()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        log_action(self.request, ActivityLog.Actions.SETTINGS, self.success_message, target=self.object)
        return response


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
class DashboardIndexView(StaffRequiredMixin, PageMetaMixin, TemplateView):
    template_name = "dashboard/index.html"
    page_title = "Overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        month_ago = now - timedelta(days=30)

        galleries = Gallery.objects.all()
        context.update(
            {
                "stat_customers": Customer.objects.count(),
                "stat_customers_new": Customer.objects.filter(created_at__gte=month_ago).count(),
                "stat_galleries": galleries.count(),
                "stat_galleries_live": galleries.live().count(),
                "stat_images": GalleryImage.objects.count(),
                "stat_storage": GalleryImage.objects.aggregate(total=Sum("file_size"))["total"] or 0,
                "stat_downloads": DownloadHistory.objects.filter(created_at__gte=month_ago).count(),
                "stat_views": galleries.aggregate(total=Sum("view_count"))["total"] or 0,
                "stat_messages_new": ContactMessage.objects.filter(status="new").count(),
                "stat_selections": AlbumRequest.objects.filter(
                    status__in=["submitted", "in_review"]
                ).count(),
                "recent_galleries": galleries.select_related("customer").order_by("-created_at")[:6],
                "expiring_galleries": galleries.expiring_soon(21).select_related("customer")[:5],
                "recent_messages": ContactMessage.objects.order_by("-created_at")[:5],
                "recent_activity": ActivityLog.objects.select_related("actor")[:10],
                "recent_albums": AlbumRequest.objects.select_related("customer", "gallery")
                .exclude(status="draft")
                .order_by("-created_at")[:5],
                "chart": self.build_chart(),
                "top_galleries": galleries.order_by("-view_count")[:5],
            }
        )
        return context

    def build_chart(self):
        """Galleries + downloads per month for the last six months."""
        today = timezone.now().date().replace(day=1)
        buckets = []
        for offset in range(5, -1, -1):
            month = today
            for _ in range(offset):
                month = (month - timedelta(days=1)).replace(day=1)
            next_month = (month + timedelta(days=32)).replace(day=1)
            buckets.append(
                {
                    "label": month.strftime("%b"),
                    "galleries": Gallery.objects.filter(
                        created_at__date__gte=month, created_at__date__lt=next_month
                    ).count(),
                    "downloads": DownloadHistory.objects.filter(
                        created_at__date__gte=month, created_at__date__lt=next_month
                    ).count(),
                }
            )
        peak = max([max(b["galleries"], b["downloads"]) for b in buckets] + [1])
        for bucket in buckets:
            bucket["gallery_pct"] = round(bucket["galleries"] / peak * 100)
            bucket["download_pct"] = round(bucket["downloads"] / peak * 100)
        return buckets


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class CustomerListView(DashboardListView):
    model = Customer
    page_title = "Customers"
    active_nav = "customers"
    search_fields = ["full_name", "email", "phone", "company"]
    create_url = "dashboard:customer_create"
    create_label = "New customer"
    edit_url = "dashboard:customer_update"
    delete_url = "dashboard:customer_delete"
    detail_url = "dashboard:customer_detail"
    empty_message = "No customers yet. Add your first client to start delivering galleries."
    columns = [
        ("Client", "full_name"),
        ("Email", "email"),
        ("Type", "get_customer_type_display"),
        ("Status", "status"),
        ("Galleries", "galleries.count"),
        ("Added", "created_at"),
    ]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("assigned_photographer", "user")
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filters"] = [("status", "Status", Customer.Status.choices)]
        return context


class CustomerCreateView(DashboardCreateView):
    model = Customer
    form_class = dash_forms.CustomerForm
    page_title = "New customer"
    active_nav = "customers"
    cancel_url = "dashboard:customer_list"
    success_message = "Customer created."
    form_intro = "Add a client record. Optionally create their login for the private client area."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:customer_detail", args=[self.object.pk])


class CustomerUpdateView(DashboardUpdateView):
    model = Customer
    form_class = dash_forms.CustomerForm
    page_title = "Edit customer"
    active_nav = "customers"
    cancel_url = "dashboard:customer_list"

    def get_success_url(self):
        return reverse("dashboard:customer_detail", args=[self.object.pk])


class CustomerDetailView(StaffRequiredMixin, PageMetaMixin, DetailView):
    model = Customer
    template_name = "dashboard/customer_detail.html"
    context_object_name = "customer"
    active_nav = "customers"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        context.update(
            {
                "page_title": customer.full_name,
                "galleries": customer.galleries.select_related("photographer").annotate(
                    photo_count=Count("images", distinct=True)
                ),
                "album_requests": customer.album_requests.select_related("gallery"),
                "downloads": customer.downloads.select_related("gallery")[:10],
                "selection_total": AlbumSelection.objects.filter(
                    customer=customer, is_selected=True
                ).count(),
            }
        )
        return context


class CustomerDeleteView(AdminRequiredMixin, DashboardDeleteView):
    model = Customer
    success_url = reverse_lazy("dashboard:customer_list")
    page_title = "Delete customer"
    active_nav = "customers"
    success_message = "Customer deleted."


# ---------------------------------------------------------------------------
# Photographers
# ---------------------------------------------------------------------------
class PhotographerListView(DashboardListView):
    model = Photographer
    page_title = "Photographers"
    active_nav = "team"
    search_fields = ["display_name", "email", "specialties"]
    create_url = "dashboard:photographer_create"
    create_label = "New photographer"
    edit_url = "dashboard:photographer_update"
    delete_url = "dashboard:photographer_delete"
    columns = [
        ("Name", "display_name"),
        ("Title", "title"),
        ("Email", "email"),
        ("Galleries", "gallery_count"),
        ("Active", "is_active"),
    ]


class PhotographerCreateView(DashboardCreateView):
    model = Photographer
    form_class = dash_forms.PhotographerForm
    page_title = "New photographer"
    active_nav = "team"
    cancel_url = "dashboard:photographer_list"
    success_url = reverse_lazy("dashboard:photographer_list")


class PhotographerUpdateView(DashboardUpdateView):
    model = Photographer
    form_class = dash_forms.PhotographerForm
    page_title = "Edit photographer"
    active_nav = "team"
    cancel_url = "dashboard:photographer_list"
    success_url = reverse_lazy("dashboard:photographer_list")


class PhotographerDeleteView(AdminRequiredMixin, DashboardDeleteView):
    model = Photographer
    success_url = reverse_lazy("dashboard:photographer_list")
    page_title = "Delete photographer"
    active_nav = "team"


# ---------------------------------------------------------------------------
# Galleries
# ---------------------------------------------------------------------------
class GalleryListView(DashboardListView):
    model = Gallery
    template_name = "dashboard/gallery_list.html"
    page_title = "Galleries"
    active_nav = "galleries"
    search_fields = ["title", "customer__full_name", "access_code"]
    create_url = "dashboard:gallery_create"
    create_label = "New gallery"
    paginate_by = 15

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("customer", "photographer", "category")
            .annotate(
                photo_count=Count("images", distinct=True),
                pick_count=Count("selections", filter=Q(selections__is_selected=True), distinct=True),
            )
            .order_by("-created_at")
        )
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Gallery.Status.choices
        context["current_status"] = self.request.GET.get("status", "")
        return context


class GalleryCreateView(DashboardCreateView):
    model = Gallery
    form_class = dash_forms.GalleryForm
    page_title = "New gallery"
    active_nav = "galleries"
    cancel_url = "dashboard:gallery_list"
    success_message = "Gallery created. Upload the photographs next."
    form_intro = "Create the delivery gallery, then upload images from the gallery page."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:gallery_detail", args=[self.object.pk])


class GalleryUpdateView(DashboardUpdateView):
    model = Gallery
    form_class = dash_forms.GalleryForm
    page_title = "Edit gallery"
    active_nav = "galleries"
    cancel_url = "dashboard:gallery_list"

    def get_success_url(self):
        return reverse("dashboard:gallery_detail", args=[self.object.pk])


class GalleryDetailView(StaffRequiredMixin, PageMetaMixin, DetailView):
    model = Gallery
    template_name = "dashboard/gallery_detail.html"
    context_object_name = "gallery"
    active_nav = "galleries"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gallery = self.object
        context.update(
            {
                "page_title": gallery.title,
                "images": gallery.images.order_by("order", "id"),
                "upload_form": dash_forms.GalleryBulkUploadForm(),
                "selections": AlbumSelection.objects.filter(gallery=gallery, is_selected=True)
                .select_related("image", "customer")[:60],
                "album_requests": gallery.album_requests.select_related("customer"),
                "access_logs": gallery.access_logs.select_related("user")[:15],
                "downloads": gallery.downloads.select_related("user", "image")[:15],
                "share_url": self.request.build_absolute_uri(gallery.get_share_url()),
                "client_url": self.request.build_absolute_uri(gallery.get_absolute_url()),
            }
        )
        return context


class GalleryDeleteView(AdminRequiredMixin, DashboardDeleteView):
    model = Gallery
    success_url = reverse_lazy("dashboard:gallery_list")
    page_title = "Delete gallery"
    active_nav = "galleries"
    success_message = "Gallery and all its images were deleted."


class GalleryUploadView(StaffRequiredMixin, View):
    """Bulk image upload endpoint for a gallery."""

    def post(self, request, pk, *args, **kwargs):
        gallery = get_object_or_404(Gallery, pk=pk)
        files = request.FILES.getlist("images")
        if not files:
            messages.warning(request, "No files were selected.")
            return redirect(gallery.get_dashboard_url())

        start_order = (gallery.images.count() or 0)
        created = 0
        skipped = 0
        for index, upload in enumerate(files):
            content_type = (upload.content_type or "").lower()
            if not content_type.startswith("image/"):
                skipped += 1
                continue
            GalleryImage.objects.create(
                gallery=gallery,
                image=upload,
                filename=upload.name[:220],
                order=start_order + index,
                uploaded_by=request.user,
            )
            created += 1

        if created and not gallery.cover_image:
            first = gallery.images.order_by("order").first()
            if first:
                first.is_cover = True
                first.save(update_fields=["is_cover", "updated_at"])

        log_action(
            request,
            ActivityLog.Actions.UPLOAD,
            f"Uploaded {created} image(s) to '{gallery.title}'.",
            target=gallery,
            created=created,
            skipped=skipped,
        )
        if created:
            messages.success(request, f"{created} photograph(s) uploaded.")
        if skipped:
            messages.warning(request, f"{skipped} file(s) were skipped (not images).")
        return redirect(gallery.get_dashboard_url())


class GalleryImageDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        image = get_object_or_404(GalleryImage.objects.select_related("gallery"), pk=pk)
        gallery = image.gallery
        image.delete()
        log_action(request, ActivityLog.Actions.DELETE, f"Removed an image from '{gallery.title}'.", gallery)
        messages.success(request, "Photograph removed.")
        return redirect(gallery.get_dashboard_url())


class GalleryImageCoverView(StaffRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        image = get_object_or_404(GalleryImage.objects.select_related("gallery"), pk=pk)
        gallery = image.gallery
        gallery.images.update(is_cover=False)
        GalleryImage.objects.filter(pk=image.pk).update(is_cover=True)
        gallery.cover_image = image.image
        gallery.save(update_fields=["cover_image", "updated_at"])
        messages.success(request, "Cover image updated.")
        return redirect(gallery.get_dashboard_url())


class GalleryImageToggleView(StaffRequiredMixin, View):
    """Toggle hidden / highlight / download flags from the image grid."""

    def post(self, request, pk, *args, **kwargs):
        image = get_object_or_404(GalleryImage.objects.select_related("gallery"), pk=pk)
        flag = request.POST.get("flag")
        if flag in {"is_hidden", "is_highlight", "allow_download"}:
            setattr(image, flag, not getattr(image, flag))
            image.save(update_fields=[flag, "updated_at"])
            messages.success(request, "Image updated.")
        return redirect(image.gallery.get_dashboard_url())


class GalleryImageReorderView(StaffRequiredMixin, View):
    """Accepts a JSON array of image ids in their new display order."""

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"ok": False, "error": "Invalid payload."}, status=400)
        order = payload.get("order") or []
        for index, image_id in enumerate(order):
            GalleryImage.objects.filter(pk=image_id).update(order=index)
        return JsonResponse({"ok": True, "count": len(order)})


class GalleryRotateCodeView(StaffRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        gallery = get_object_or_404(Gallery, pk=pk)
        code = gallery.rotate_access_code()
        messages.success(request, f"New access code generated: {code}")
        log_action(request, ActivityLog.Actions.UPDATE, f"Rotated access code for '{gallery.title}'.", gallery)
        return redirect(gallery.get_dashboard_url())


class GalleryNotifyView(StaffRequiredMixin, View):
    """Manually (re)send the delivery notification to the client."""

    def post(self, request, pk, *args, **kwargs):
        from apps.notifications.services import notify_customer

        gallery = get_object_or_404(Gallery.objects.select_related("customer"), pk=pk)
        notify_customer(
            customer=gallery.customer,
            title="Your gallery is ready",
            message=f"'{gallery.title}' is available in your private client area.",
            category="gallery",
            level="success",
            url=gallery.get_absolute_url(),
            gallery=gallery,
            actor=request.user,
            email_subject=f"[MS Photo Studio] Your gallery '{gallery.title}' is ready",
        )
        Gallery.objects.filter(pk=gallery.pk).update(notified_at=timezone.now())
        messages.success(request, f"Notification sent to {gallery.customer.email}.")
        return redirect(gallery.get_dashboard_url())


class GalleryCategoryListView(DashboardListView):
    model = GalleryCategory
    page_title = "Gallery categories"
    active_nav = "galleries"
    search_fields = ["name"]
    create_url = "dashboard:gallery_category_create"
    edit_url = "dashboard:gallery_category_update"
    delete_url = "dashboard:gallery_category_delete"
    columns = [("Name", "name"), ("Galleries", "galleries.count"), ("Order", "order"), ("Active", "is_active")]


class GalleryCategoryCreateView(DashboardCreateView):
    model = GalleryCategory
    form_class = dash_forms.GalleryCategoryForm
    page_title = "New gallery category"
    active_nav = "galleries"
    cancel_url = "dashboard:gallery_category_list"
    success_url = reverse_lazy("dashboard:gallery_category_list")


class GalleryCategoryUpdateView(DashboardUpdateView):
    model = GalleryCategory
    form_class = dash_forms.GalleryCategoryForm
    page_title = "Edit gallery category"
    active_nav = "galleries"
    cancel_url = "dashboard:gallery_category_list"
    success_url = reverse_lazy("dashboard:gallery_category_list")


class GalleryCategoryDeleteView(DashboardDeleteView):
    model = GalleryCategory
    success_url = reverse_lazy("dashboard:gallery_category_list")
    page_title = "Delete gallery category"
    active_nav = "galleries"


# ---------------------------------------------------------------------------
# Album requests / selections
# ---------------------------------------------------------------------------
class AlbumRequestListView(DashboardListView):
    model = AlbumRequest
    page_title = "Album requests"
    active_nav = "albums"
    search_fields = ["title", "customer__full_name", "gallery__title"]
    detail_url = "dashboard:album_detail"
    columns = [
        ("Request", "title"),
        ("Client", "customer.full_name"),
        ("Gallery", "gallery.title"),
        ("Picks", "selection_count"),
        ("Status", "status"),
        ("Submitted", "submitted_at"),
    ]
    empty_message = "No album requests have been submitted yet."

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "gallery")


class AlbumRequestDetailView(StaffRequiredMixin, PageMetaMixin, UpdateView):
    model = AlbumRequest
    form_class = dash_forms.AlbumRequestForm
    template_name = "dashboard/album_detail.html"
    context_object_name = "album"
    active_nav = "albums"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        album = self.object
        context["page_title"] = str(album)
        context["selections"] = album.selections.filter(is_selected=True).select_related("image")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.status == AlbumRequest.Status.APPROVED and not self.object.approved_at:
            AlbumRequest.objects.filter(pk=self.object.pk).update(approved_at=timezone.now())
        if self.object.status == AlbumRequest.Status.COMPLETED and not self.object.completed_at:
            AlbumRequest.objects.filter(pk=self.object.pk).update(completed_at=timezone.now())
        messages.success(self.request, "Album request updated.")
        return response

    def get_success_url(self):
        return reverse("dashboard:album_detail", args=[self.object.pk])


# ---------------------------------------------------------------------------
# Enquiries
# ---------------------------------------------------------------------------
class ContactMessageListView(DashboardListView):
    model = ContactMessage
    page_title = "Enquiries"
    active_nav = "messages"
    search_fields = ["name", "email", "subject", "message"]
    detail_url = "dashboard:message_detail"
    columns = [
        ("From", "name"),
        ("Email", "email"),
        ("Subject", "display_subject"),
        ("Status", "status"),
        ("Received", "created_at"),
    ]
    empty_message = "No enquiries yet."


class ContactMessageDetailView(StaffRequiredMixin, PageMetaMixin, UpdateView):
    model = ContactMessage
    form_class = dash_forms.ContactMessageForm
    template_name = "dashboard/message_detail.html"
    context_object_name = "message_obj"
    active_nav = "messages"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.status == ContactMessage.Status.NEW:
            ContactMessage.objects.filter(pk=obj.pk).update(status=ContactMessage.Status.READ)
            obj.status = ContactMessage.Status.READ
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.display_subject
        return context

    def form_valid(self, form):
        form.instance.handled_by = self.request.user
        if form.instance.status == ContactMessage.Status.REPLIED and not form.instance.replied_at:
            form.instance.replied_at = timezone.now()
        messages.success(self.request, "Enquiry updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:message_list")


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------
class PortfolioCategoryListView(DashboardListView):
    model = PortfolioCategory
    page_title = "Portfolio collections"
    active_nav = "portfolio"
    search_fields = ["name", "subtitle"]
    create_url = "dashboard:portfolio_category_create"
    create_label = "New collection"
    edit_url = "dashboard:portfolio_category_update"
    delete_url = "dashboard:portfolio_category_delete"
    columns = [("Collection", "name"), ("Photos", "image_count"), ("Featured", "is_featured"),
               ("Order", "order"), ("Active", "is_active")]


class PortfolioCategoryCreateView(DashboardCreateView):
    model = PortfolioCategory
    form_class = dash_forms.PortfolioCategoryForm
    page_title = "New collection"
    active_nav = "portfolio"
    cancel_url = "dashboard:portfolio_category_list"
    success_url = reverse_lazy("dashboard:portfolio_category_list")


class PortfolioCategoryUpdateView(DashboardUpdateView):
    model = PortfolioCategory
    form_class = dash_forms.PortfolioCategoryForm
    page_title = "Edit collection"
    active_nav = "portfolio"
    cancel_url = "dashboard:portfolio_category_list"
    success_url = reverse_lazy("dashboard:portfolio_category_list")


class PortfolioCategoryDeleteView(AdminRequiredMixin, DashboardDeleteView):
    model = PortfolioCategory
    success_url = reverse_lazy("dashboard:portfolio_category_list")
    page_title = "Delete collection"
    active_nav = "portfolio"


class PortfolioImageListView(StaffRequiredMixin, PageMetaMixin, ListView):
    model = PortfolioImage
    template_name = "dashboard/portfolio_images.html"
    context_object_name = "images"
    paginate_by = 36
    page_title = "Portfolio photographs"
    active_nav = "portfolio"

    def get_queryset(self):
        queryset = PortfolioImage.objects.select_related("category").order_by("category", "order")
        category = self.request.GET.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = PortfolioCategory.objects.all()
        context["current_category"] = self.request.GET.get("category", "")
        context["upload_form"] = dash_forms.PortfolioBulkUploadForm()
        return context


class PortfolioBulkUploadView(StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = dash_forms.PortfolioBulkUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Choose a collection before uploading.")
            return redirect("dashboard:portfolio_image_list")
        category = form.cleaned_data["category"]
        files = request.FILES.getlist("images")
        start = category.images.count()
        created = 0
        for index, upload in enumerate(files):
            if not (upload.content_type or "").startswith("image/"):
                continue
            PortfolioImage.objects.create(
                category=category,
                image=upload,
                title=upload.name.rsplit(".", 1)[0][:180],
                order=start + index,
            )
            created += 1
        log_action(request, ActivityLog.Actions.UPLOAD, f"Uploaded {created} portfolio image(s).", category)
        messages.success(request, f"{created} photograph(s) added to {category.name}.")
        return redirect("dashboard:portfolio_image_list")


class PortfolioImageCreateView(DashboardCreateView):
    model = PortfolioImage
    form_class = dash_forms.PortfolioImageForm
    page_title = "Add photograph"
    active_nav = "portfolio"
    cancel_url = "dashboard:portfolio_image_list"
    success_url = reverse_lazy("dashboard:portfolio_image_list")


class PortfolioImageUpdateView(DashboardUpdateView):
    model = PortfolioImage
    form_class = dash_forms.PortfolioImageForm
    page_title = "Edit photograph"
    active_nav = "portfolio"
    cancel_url = "dashboard:portfolio_image_list"
    success_url = reverse_lazy("dashboard:portfolio_image_list")


class PortfolioImageDeleteView(DashboardDeleteView):
    model = PortfolioImage
    success_url = reverse_lazy("dashboard:portfolio_image_list")
    page_title = "Delete photograph"
    active_nav = "portfolio"


# ---------------------------------------------------------------------------
# Services & CMS collections
# ---------------------------------------------------------------------------
class ServiceListView(DashboardListView):
    model = Service
    page_title = "Services"
    active_nav = "services"
    search_fields = ["title", "tagline"]
    create_url = "dashboard:service_create"
    create_label = "New service"
    edit_url = "dashboard:service_update"
    delete_url = "dashboard:service_delete"
    columns = [("Service", "title"), ("From", "price_display"), ("Featured", "is_featured"),
               ("Order", "order"), ("Active", "is_active")]


class ServiceCreateView(DashboardCreateView):
    model = Service
    form_class = dash_forms.ServiceForm
    page_title = "New service"
    active_nav = "services"
    cancel_url = "dashboard:service_list"
    success_url = reverse_lazy("dashboard:service_list")


class ServiceUpdateView(DashboardUpdateView):
    model = Service
    form_class = dash_forms.ServiceForm
    page_title = "Edit service"
    active_nav = "services"
    cancel_url = "dashboard:service_list"
    success_url = reverse_lazy("dashboard:service_list")


class ServiceDeleteView(DashboardDeleteView):
    model = Service
    success_url = reverse_lazy("dashboard:service_list")
    page_title = "Delete service"
    active_nav = "services"


class TeamMemberListView(DashboardListView):
    model = TeamMember
    page_title = "Team"
    active_nav = "team"
    search_fields = ["name", "role"]
    create_url = "dashboard:team_create"
    create_label = "New team member"
    edit_url = "dashboard:team_update"
    delete_url = "dashboard:team_delete"
    columns = [("Name", "name"), ("Role", "role"), ("Order", "order"), ("Active", "is_active")]


class TeamMemberCreateView(DashboardCreateView):
    model = TeamMember
    form_class = dash_forms.TeamMemberForm
    page_title = "New team member"
    active_nav = "team"
    cancel_url = "dashboard:team_list"
    success_url = reverse_lazy("dashboard:team_list")


class TeamMemberUpdateView(DashboardUpdateView):
    model = TeamMember
    form_class = dash_forms.TeamMemberForm
    page_title = "Edit team member"
    active_nav = "team"
    cancel_url = "dashboard:team_list"
    success_url = reverse_lazy("dashboard:team_list")


class TeamMemberDeleteView(DashboardDeleteView):
    model = TeamMember
    success_url = reverse_lazy("dashboard:team_list")
    page_title = "Delete team member"
    active_nav = "team"


class FAQListView(DashboardListView):
    model = FAQ
    page_title = "FAQs"
    active_nav = "cms"
    search_fields = ["question", "answer"]
    create_url = "dashboard:faq_create"
    create_label = "New FAQ"
    edit_url = "dashboard:faq_update"
    delete_url = "dashboard:faq_delete"
    columns = [("Question", "question"), ("Category", "get_category_display"),
               ("Order", "order"), ("Active", "is_active")]


class FAQCreateView(DashboardCreateView):
    model = FAQ
    form_class = dash_forms.FAQForm
    page_title = "New FAQ"
    active_nav = "cms"
    cancel_url = "dashboard:faq_list"
    success_url = reverse_lazy("dashboard:faq_list")


class FAQUpdateView(DashboardUpdateView):
    model = FAQ
    form_class = dash_forms.FAQForm
    page_title = "Edit FAQ"
    active_nav = "cms"
    cancel_url = "dashboard:faq_list"
    success_url = reverse_lazy("dashboard:faq_list")


class FAQDeleteView(DashboardDeleteView):
    model = FAQ
    success_url = reverse_lazy("dashboard:faq_list")
    page_title = "Delete FAQ"
    active_nav = "cms"


class TestimonialListView(DashboardListView):
    model = Testimonial
    page_title = "Testimonials"
    active_nav = "cms"
    search_fields = ["author_name", "quote"]
    create_url = "dashboard:testimonial_create"
    create_label = "New testimonial"
    edit_url = "dashboard:testimonial_update"
    delete_url = "dashboard:testimonial_delete"
    columns = [("Author", "author_name"), ("Role", "author_role"), ("Rating", "rating"),
               ("Featured", "is_featured"), ("Active", "is_active")]


class TestimonialCreateView(DashboardCreateView):
    model = Testimonial
    form_class = dash_forms.TestimonialForm
    page_title = "New testimonial"
    active_nav = "cms"
    cancel_url = "dashboard:testimonial_list"
    success_url = reverse_lazy("dashboard:testimonial_list")


class TestimonialUpdateView(DashboardUpdateView):
    model = Testimonial
    form_class = dash_forms.TestimonialForm
    page_title = "Edit testimonial"
    active_nav = "cms"
    cancel_url = "dashboard:testimonial_list"
    success_url = reverse_lazy("dashboard:testimonial_list")


class TestimonialDeleteView(DashboardDeleteView):
    model = Testimonial
    success_url = reverse_lazy("dashboard:testimonial_list")
    page_title = "Delete testimonial"
    active_nav = "cms"


# ---------------------------------------------------------------------------
# Settings, analytics, notifications
# ---------------------------------------------------------------------------
class WebsiteSettingsView(DashboardSingletonUpdateView):
    model = WebsiteSettings
    form_class = dash_forms.WebsiteSettingsForm
    page_title = "Website settings"
    active_nav = "settings"
    success_url = reverse_lazy("dashboard:settings_site")


class SEOSettingsView(DashboardSingletonUpdateView):
    model = SEOSettings
    form_class = dash_forms.SEOSettingsForm
    page_title = "SEO settings"
    active_nav = "settings"
    success_url = reverse_lazy("dashboard:settings_seo")


class AnalyticsView(StaffRequiredMixin, PageMetaMixin, TemplateView):
    template_name = "dashboard/analytics.html"
    page_title = "Analytics"
    active_nav = "analytics"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        context.update(
            {
                "views_total": Gallery.objects.aggregate(t=Sum("view_count"))["t"] or 0,
                "downloads_total": DownloadHistory.objects.count(),
                "downloads_week": DownloadHistory.objects.filter(created_at__gte=week_ago).count(),
                "downloads_month": DownloadHistory.objects.filter(created_at__gte=month_ago).count(),
                "selections_total": AlbumSelection.objects.filter(is_selected=True).count(),
                "top_galleries": Gallery.objects.select_related("customer").order_by("-view_count")[:10],
                "top_downloaded": Gallery.objects.select_related("customer").order_by("-download_count")[:10],
                "busiest_clients": Customer.objects.annotate(
                    total=Count("galleries", distinct=True)
                ).order_by("-total")[:8],
                "access_logs": GalleryAccessLog.objects.select_related("gallery", "user")[:25],
                "activity": ActivityLog.objects.select_related("actor")[:25],
                "action_breakdown": (
                    GalleryAccessLog.objects.values("action")
                    .annotate(total=Count("id"))
                    .order_by("-total")[:8]
                ),
                "storage_bytes": GalleryImage.objects.aggregate(t=Sum("file_size"))["t"] or 0,
                "image_count": GalleryImage.objects.count(),
            }
        )
        return context


class NotificationListView(StaffRequiredMixin, PageMetaMixin, ListView):
    template_name = "dashboard/notifications.html"
    context_object_name = "notifications"
    paginate_by = 30
    page_title = "Notifications"
    active_nav = "notifications"

    def get_queryset(self):
        return Notification.objects.for_user(self.request.user).select_related("related_gallery")

    def post(self, request, *args, **kwargs):
        Notification.objects.for_user(request.user).unread().update(
            is_read=True, read_at=timezone.now()
        )
        messages.success(request, "Notifications cleared.")
        return redirect("dashboard:notifications")


class ActivityLogView(StaffRequiredMixin, PageMetaMixin, ListView):
    template_name = "dashboard/activity.html"
    context_object_name = "entries"
    paginate_by = 50
    page_title = "Activity log"
    active_nav = "analytics"

    def get_queryset(self):
        queryset = ActivityLog.objects.select_related("actor")
        action = self.request.GET.get("action")
        if action:
            queryset = queryset.filter(action=action)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["actions"] = ActivityLog.Actions.choices
        context["current_action"] = self.request.GET.get("action", "")
        return context


# ---------------------------------------------------------------------------
# Studio team logins
# ---------------------------------------------------------------------------
class StaffUserListView(AdminRequiredMixin, DashboardListView):
    page_title = "Studio logins"
    active_nav = "settings"
    search_fields = ["username", "email", "first_name", "last_name"]
    create_url = "dashboard:staff_create"
    create_label = "New login"
    edit_url = "dashboard:staff_update"
    columns = [("User", "get_display_name"), ("Username", "username"), ("Email", "email"),
               ("Role", "get_role_display"), ("Active", "is_active"), ("Last login", "last_login")]

    def get_queryset(self):
        from django.contrib.auth import get_user_model

        self.queryset = get_user_model().objects.all().order_by("role", "username")
        return super().get_queryset()


class StaffUserCreateView(AdminRequiredMixin, DashboardCreateView):
    page_title = "New studio login"
    active_nav = "settings"
    cancel_url = "dashboard:staff_list"
    success_url = reverse_lazy("dashboard:staff_list")

    def get_form_class(self):
        from apps.accounts.forms import StaffUserForm

        return StaffUserForm

    def get_queryset(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.all()


class StaffUserUpdateView(AdminRequiredMixin, DashboardUpdateView):
    page_title = "Edit studio login"
    active_nav = "settings"
    cancel_url = "dashboard:staff_list"
    success_url = reverse_lazy("dashboard:staff_list")

    def get_form_class(self):
        from apps.accounts.forms import StaffUserForm

        return StaffUserForm

    def get_queryset(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.all()