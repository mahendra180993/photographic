"""Editable website content: settings, SEO, team, FAQ, testimonials, messages."""

from django.conf import settings as django_settings
from django.db import models

from apps.common.models import (
    ActiveManager,
    OrderedActiveModel,
    SingletonModel,
    SluggedModel,
    TimeStampedModel,
    UUIDModel,
)
from apps.common.utils import branding_path, team_photo_path, testimonial_photo_path


class WebsiteSettings(SingletonModel, TimeStampedModel):
    """Global brand + contact configuration edited from the studio dashboard."""

    site_name = models.CharField(max_length=120, default="MS Photo Studio")
    tagline = models.CharField(max_length=200, default="Photography for the quietly extraordinary")
    logo = models.ImageField(upload_to=branding_path, blank=True, null=True)
    logo_light = models.ImageField(upload_to=branding_path, blank=True, null=True)
    favicon = models.ImageField(upload_to=branding_path, blank=True, null=True)

    hero_eyebrow = models.CharField(max_length=120, blank=True, default="Fine art photography studio")
    hero_title = models.CharField(max_length=200, default="Light, held still.")
    hero_subtitle = models.TextField(
        blank=True,
        default="A boutique atelier crafting timeless imagery for weddings, editorial and brands.",
    )
    hero_image = models.ImageField(upload_to=branding_path, blank=True, null=True)
    hero_video_url = models.URLField(blank=True)
    hero_cta_label = models.CharField(max_length=60, blank=True, default="View the portfolio")

    about_title = models.CharField(max_length=200, blank=True, default="The atelier")
    about_intro = models.TextField(blank=True)
    about_body = models.TextField(blank=True)
    about_image = models.ImageField(upload_to=branding_path, blank=True, null=True)
    years_experience = models.PositiveIntegerField(default=12)
    projects_delivered = models.PositiveIntegerField(default=480)
    awards_count = models.PositiveIntegerField(default=17)
    countries_count = models.PositiveIntegerField(default=23)

    email = models.EmailField(blank=True, default="studio@msphotostudio.com")
    booking_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True, default="+33 1 84 80 00 00")
    whatsapp = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=240, blank=True, default="18 Rue des Lumieres")
    city = models.CharField(max_length=120, blank=True, default="Paris")
    postcode = models.CharField(max_length=20, blank=True, default="75003")
    country = models.CharField(max_length=120, blank=True, default="France")
    opening_hours = models.CharField(max_length=180, blank=True, default="Mon - Fri, 09:00 - 18:00 CET")
    map_embed_url = models.URLField(blank=True)

    instagram = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    pinterest = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    vimeo = models.URLField(blank=True)
    behance = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    primary_color = models.CharField(max_length=9, default="#0B0B0C")
    accent_color = models.CharField(max_length=9, default="#D4AF37")
    surface_color = models.CharField(max_length=9, default="#F6F5F2")

    footer_note = models.CharField(
        max_length=240,
        blank=True,
        default="Crafted with care in Paris.",
    )
    announcement = models.CharField(max_length=200, blank=True)
    announcement_active = models.BooleanField(default=False)
    is_maintenance = models.BooleanField(default=False)
    maintenance_message = models.TextField(
        blank=True,
        default="We are polishing something beautiful. Back shortly.",
    )
    enable_client_area = models.BooleanField(default=True)
    enable_contact_form = models.BooleanField(default=True)

    class Meta:
        verbose_name = "website settings"
        verbose_name_plural = "website settings"

    def __str__(self):
        return self.site_name

    @property
    def full_address(self):
        parts = [self.address, f"{self.postcode} {self.city}".strip(), self.country]
        return ", ".join(part for part in parts if part)

    @property
    def social_links(self):
        candidates = [
            ("Instagram", self.instagram),
            ("Facebook", self.facebook),
            ("Pinterest", self.pinterest),
            ("YouTube", self.youtube),
            ("Vimeo", self.vimeo),
            ("Behance", self.behance),
            ("LinkedIn", self.linkedin),
        ]
        return [(name, url) for name, url in candidates if url]

    @property
    def contact_email(self):
        return self.booking_email or self.email or django_settings.DEFAULT_FROM_EMAIL


class SEOSettings(SingletonModel, TimeStampedModel):
    meta_title = models.CharField(max_length=180, default="MS Photo Studio | Fine Art Photography Studio")
    meta_description = models.TextField(
        max_length=320,
        default=(
            "MS Photo Studio is a boutique photography studio creating timeless "
            "wedding, editorial and brand imagery worldwide."
        ),
    )
    meta_keywords = models.CharField(
        max_length=320,
        blank=True,
        default="photography studio, wedding photographer, editorial photography, fine art",
    )
    og_image = models.ImageField(upload_to=branding_path, blank=True, null=True)
    twitter_handle = models.CharField(max_length=60, blank=True)
    canonical_domain = models.URLField(blank=True, default="http://localhost:8000")
    google_analytics_id = models.CharField(max_length=40, blank=True)
    google_site_verification = models.CharField(max_length=120, blank=True)
    structured_data_enabled = models.BooleanField(default=True)
    sitemap_enabled = models.BooleanField(default=True)
    robots_txt = models.TextField(
        blank=True,
        default="User-agent: *\nDisallow: /studio/\nDisallow: /client/\nAllow: /\n",
    )

    class Meta:
        verbose_name = "SEO settings"
        verbose_name_plural = "SEO settings"

    def __str__(self):
        return "SEO settings"


class TeamMember(UUIDModel, TimeStampedModel, OrderedActiveModel, SluggedModel):
    slug_source_field = "name"

    name = models.CharField(max_length=140)
    role = models.CharField(max_length=140, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to=team_photo_path, blank=True, null=True)
    email = models.EmailField(blank=True)
    instagram = models.CharField(max_length=120, blank=True)
    linkedin = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta(OrderedActiveModel.Meta):
        ordering = ("order", "name")

    def __str__(self):
        return self.name


class FAQ(UUIDModel, TimeStampedModel, OrderedActiveModel):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        BOOKING = "booking", "Booking"
        DELIVERY = "delivery", "Delivery & galleries"
        PRICING = "pricing", "Pricing"

    question = models.CharField(max_length=260)
    answer = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)

    class Meta(OrderedActiveModel.Meta):
        ordering = ("order", "id")
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class Testimonial(UUIDModel, TimeStampedModel, OrderedActiveModel):
    author_name = models.CharField(max_length=140)
    author_role = models.CharField(max_length=160, blank=True)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    photo = models.ImageField(upload_to=testimonial_photo_path, blank=True, null=True)
    event_type = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta(OrderedActiveModel.Meta):
        ordering = ("order", "-created_at")

    def __str__(self):
        return f"{self.author_name} - {self.quote[:40]}"

    @property
    def star_range(self):
        return range(max(0, min(5, self.rating)))


class ContactMessage(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        READ = "read", "Read"
        REPLIED = "replied", "Replied"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=140)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    event_type = models.CharField(max_length=120, blank=True)
    event_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=160, blank=True)
    budget = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=120, blank=True, default="website")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=400, blank=True)
    handled_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_messages",
    )
    internal_notes = models.TextField(blank=True)
    replied_at = models.DateTimeField(blank=True, null=True)

    objects = models.Manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_new(self):
        return self.status == self.Status.NEW

    @property
    def display_subject(self):
        return self.subject or f"Enquiry from {self.name}"