"""Public-facing marketing pages."""

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from apps.cms.models import FAQ, ContactMessage, TeamMember, Testimonial
from apps.common.mixins import PageMetaMixin
from apps.common.utils import get_client_ip, get_user_agent
from apps.portfolio.models import PortfolioCategory, PortfolioImage
from apps.services.models import Service

from .forms import ContactForm


class HomeView(PageMetaMixin, TemplateView):
    template_name = "website/home.html"
    active_nav = "home"
    meta_description = (
        "Lumina Atelier - a boutique photography studio crafting timeless wedding, "
        "editorial and brand imagery."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "featured_categories": (
                    PortfolioCategory.objects.active()
                    .annotate(photo_count=Count("images", filter=Q(images__is_active=True)))
                    .order_by("order", "name")[:6]
                ),
                "featured_images": (
                    PortfolioImage.objects.active()
                    .select_related("category")
                    .filter(is_featured=True)[:9]
                    or PortfolioImage.objects.active().select_related("category")[:9]
                ),
                "services": Service.objects.active().order_by("order")[:4],
                "testimonials": Testimonial.objects.active().filter(is_featured=True)[:6]
                or Testimonial.objects.active()[:6],
                "team": TeamMember.objects.active()[:4],
            }
        )
        return context


class AboutView(PageMetaMixin, TemplateView):
    template_name = "website/about.html"
    active_nav = "about"
    page_title = "The studio"
    meta_description = "Meet the photographers and craftspeople behind Lumina Atelier."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "team": TeamMember.objects.active(),
                "faqs": FAQ.objects.active(),
                "testimonials": Testimonial.objects.active()[:4],
            }
        )
        return context


class PortfolioListView(PageMetaMixin, ListView):
    template_name = "website/portfolio_list.html"
    context_object_name = "categories"
    active_nav = "portfolio"
    page_title = "Portfolio"
    meta_description = "Selected work from the Lumina Atelier archive."

    def get_queryset(self):
        return (
            PortfolioCategory.objects.active()
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=PortfolioImage.objects.active().order_by("order", "-created_at")[:8],
                    to_attr="preview_images",
                )
            )
            .annotate(photo_count=Count("images", filter=Q(images__is_active=True)))
            .order_by("order", "name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_images"] = (
            PortfolioImage.objects.active().select_related("category").order_by("order", "-created_at")[:36]
        )
        return context


class PortfolioDetailView(PageMetaMixin, DetailView):
    template_name = "website/portfolio_detail.html"
    context_object_name = "category"
    active_nav = "portfolio"

    def get_object(self, queryset=None):
        return get_object_or_404(PortfolioCategory.objects.active(), slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = context["category"]
        context["images"] = category.images.filter(is_active=True).order_by("order", "-created_at")
        context["page_title"] = category.name
        context["meta_description"] = category.description[:200] or self.meta_description
        context["other_categories"] = (
            PortfolioCategory.objects.active().exclude(pk=category.pk).order_by("order")[:4]
        )
        return context


class ServiceListView(PageMetaMixin, ListView):
    template_name = "website/service_list.html"
    context_object_name = "services"
    active_nav = "services"
    page_title = "Services"
    meta_description = "Wedding, editorial, brand and fine-art photography packages."

    def get_queryset(self):
        return Service.objects.active().order_by("order", "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["faqs"] = FAQ.objects.active().filter(category__in=["pricing", "booking"])[:6]
        context["testimonials"] = Testimonial.objects.active()[:3]
        return context


class ServiceDetailView(PageMetaMixin, DetailView):
    template_name = "website/service_detail.html"
    context_object_name = "service"
    active_nav = "services"

    def get_object(self, queryset=None):
        return get_object_or_404(Service.objects.active(), slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = context["service"]
        context["page_title"] = service.title
        context["meta_description"] = service.short_description or service.tagline
        context["other_services"] = Service.objects.active().exclude(pk=service.pk)[:3]
        context["faqs"] = FAQ.objects.active()[:5]
        return context


class TestimonialListView(PageMetaMixin, ListView):
    template_name = "website/testimonials.html"
    context_object_name = "testimonials"
    active_nav = "testimonials"
    page_title = "Kind words"
    meta_description = "What our clients say about working with Lumina Atelier."

    def get_queryset(self):
        return Testimonial.objects.active()


class ContactView(PageMetaMixin, CreateView):
    template_name = "website/contact.html"
    form_class = ContactForm
    model = ContactMessage
    success_url = reverse_lazy("website:contact_thanks")
    active_nav = "contact"
    page_title = "Contact"
    meta_description = "Enquire about availability, packages and commissions."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["faqs"] = FAQ.objects.active()[:6]
        context["services"] = Service.objects.active()[:6]
        return context

    def form_valid(self, form):
        form.instance.ip_address = get_client_ip(self.request)
        form.instance.user_agent = get_user_agent(self.request)
        form.instance.source = self.request.GET.get("ref", "website")[:120]
        response = super().form_valid(form)
        messages.success(self.request, "Thank you - your enquiry is on its way to the studio.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please review the highlighted fields.")
        return super().form_invalid(form)


class ContactThanksView(PageMetaMixin, TemplateView):
    template_name = "website/contact_thanks.html"
    active_nav = "contact"
    page_title = "Message received"