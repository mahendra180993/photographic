"""Model forms used across the studio dashboard."""

from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from apps.albums.models import AlbumRequest
from apps.cms.models import FAQ, ContactMessage, SEOSettings, TeamMember, Testimonial, WebsiteSettings
from apps.customers.models import Customer, Photographer
from apps.galleries.models import Gallery, GalleryCategory, GalleryImage
from apps.portfolio.models import PortfolioCategory, PortfolioImage
from apps.services.models import Service

User = get_user_model()

BASE_INPUT = (
    "w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800 "
    "placeholder-slate-400 shadow-sm outline-none transition focus:border-gold focus:ring-2 "
    "focus:ring-gold/20"
)
CHECKBOX = "h-4 w-4 rounded border-slate-300 text-gold focus:ring-gold"
FILE_INPUT = (
    "block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 "
    "file:bg-ink file:px-4 file:py-2 file:text-sm file:font-medium file:text-white "
    "hover:file:bg-ink/90"
)


class StyledFormMixin:
    """Applies the dashboard input styling to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", CHECKBOX)
            elif isinstance(widget, (forms.ClearableFileInput, forms.FileInput)):
                widget.attrs.setdefault("class", FILE_INPUT)
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", BASE_INPUT)
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.DateInput):
                widget.attrs.setdefault("class", BASE_INPUT)
                widget.attrs.setdefault("type", "date")
            elif isinstance(widget, forms.DateTimeInput):
                widget.attrs.setdefault("class", BASE_INPUT)
            else:
                widget.attrs.setdefault("class", BASE_INPUT)


class StyledModelForm(StyledFormMixin, forms.ModelForm):
    pass


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# ---------------------------------------------------------------------------
# Customers & photographers
# ---------------------------------------------------------------------------
class CustomerForm(StyledModelForm):
    create_login = forms.BooleanField(
        required=False,
        label="Create a client login",
        help_text="Generates a client account so they can open their galleries.",
    )
    login_username = forms.CharField(required=False, label="Username")
    login_password = forms.CharField(
        required=False,
        label="Temporary password",
        widget=forms.PasswordInput(render_value=True),
    )

    class Meta:
        model = Customer
        fields = [
            "full_name",
            "email",
            "phone",
            "company",
            "customer_type",
            "status",
            "address",
            "city",
            "country",
            "assigned_photographer",
            "tags",
            "notes",
            "marketing_opt_in",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_photographer"].queryset = Photographer.objects.active()
        self.fields["assigned_photographer"].required = False
        if self.instance.pk and self.instance.user_id:
            self.fields["create_login"].help_text = (
                f"This customer already signs in as '{self.instance.user.username}'."
            )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("create_login") and not self.instance.user_id:
            username = (cleaned.get("login_username") or "").strip().lower()
            if not username:
                username = slugify(cleaned.get("full_name", "client")).replace("-", ".")[:40] or "client"
                counter = 1
                base = username
                while User.objects.filter(username=username).exists():
                    counter += 1
                    username = f"{base}{counter}"
                cleaned["login_username"] = username
            elif User.objects.filter(username__iexact=username).exists():
                self.add_error("login_username", "That username is already taken.")
            if not cleaned.get("login_password"):
                self.add_error("login_password", "Set a temporary password for the client.")
        return cleaned

    def save(self, commit=True):
        customer = super().save(commit=False)
        if self.cleaned_data.get("create_login") and not customer.user_id:
            user = User.objects.create_client(
                username=self.cleaned_data["login_username"],
                email=customer.email,
                password=self.cleaned_data["login_password"],
                first_name=customer.full_name.split(" ")[0][:80],
                last_name=" ".join(customer.full_name.split(" ")[1:])[:80],
                must_change_password=True,
            )
            customer.user = user
        if commit:
            customer.save()
        return customer


class PhotographerForm(StyledModelForm):
    class Meta:
        model = Photographer
        fields = [
            "display_name",
            "slug",
            "title",
            "bio",
            "specialties",
            "email",
            "phone",
            "instagram",
            "website",
            "avatar",
            "is_lead",
            "is_active",
            "order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if slug:
            return slug
        base = slugify(self.data.get("display_name", "photographer"))[:120] or "photographer"
        candidate, counter = base, 1
        while Photographer.objects.filter(slug=candidate).exclude(pk=self.instance.pk).exists():
            counter += 1
            candidate = f"{base}-{counter}"
        return candidate


# ---------------------------------------------------------------------------
# Galleries
# ---------------------------------------------------------------------------
class GalleryForm(StyledModelForm):
    class Meta:
        model = Gallery
        fields = [
            "title",
            "customer",
            "photographer",
            "category",
            "description",
            "welcome_message",
            "cover_image",
            "event_date",
            "location",
            "status",
            "visibility",
            "access_code",
            "expires_at",
            "allow_downloads",
            "allow_bulk_download",
            "allow_selection",
            "allow_favorites",
            "selection_limit",
            "selection_deadline",
            "watermark_enabled",
            "watermark_text",
            "notify_customer",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "selection_deadline": forms.DateInput(attrs={"type": "date"}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.order_by("full_name")
        self.fields["photographer"].queryset = Photographer.objects.active()
        self.fields["category"].queryset = GalleryCategory.objects.active()
        self.fields["access_code"].help_text = "Leave blank to auto-generate for shared galleries."
        self.fields["access_code"].required = False
        if self.instance.pk and self.instance.expires_at:
            self.initial["expires_at"] = self.instance.expires_at.strftime("%Y-%m-%dT%H:%M")

    def clean_access_code(self):
        return (self.cleaned_data.get("access_code") or "").strip().upper()


class GalleryCategoryForm(StyledModelForm):
    class Meta:
        model = GalleryCategory
        fields = ["name", "description", "color", "order", "is_active"]


class GalleryImageForm(StyledModelForm):
    class Meta:
        model = GalleryImage
        fields = ["title", "caption", "alt_text", "order", "is_hidden", "is_highlight", "allow_download"]


class GalleryBulkUploadForm(forms.Form):
    images = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*", "class": FILE_INPUT}),
        required=False,
        label="Photographs",
        help_text="Select multiple files at once (JPEG, PNG, WEBP).",
    )


# ---------------------------------------------------------------------------
# Portfolio, services and CMS
# ---------------------------------------------------------------------------
class PortfolioCategoryForm(StyledModelForm):
    class Meta:
        model = PortfolioCategory
        fields = [
            "name",
            "subtitle",
            "description",
            "cover_image",
            "accent_color",
            "is_featured",
            "is_active",
            "order",
        ]


class PortfolioImageForm(StyledModelForm):
    class Meta:
        model = PortfolioImage
        fields = [
            "category",
            "title",
            "image",
            "caption",
            "alt_text",
            "location",
            "shot_on",
            "credits",
            "is_featured",
            "is_active",
            "order",
        ]
        widgets = {"shot_on": forms.DateInput(attrs={"type": "date"})}


class PortfolioBulkUploadForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=PortfolioCategory.objects.all(),
        widget=forms.Select(attrs={"class": BASE_INPUT}),
    )
    images = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*", "class": FILE_INPUT}),
        required=False,
    )


class ServiceForm(StyledModelForm):
    class Meta:
        model = Service
        fields = [
            "title",
            "tagline",
            "short_description",
            "description",
            "icon",
            "image",
            "price_from",
            "currency",
            "price_unit",
            "duration",
            "turnaround",
            "features",
            "deliverables",
            "cta_label",
            "is_featured",
            "is_active",
            "order",
        ]


class TeamMemberForm(StyledModelForm):
    class Meta:
        model = TeamMember
        fields = ["name", "role", "bio", "photo", "email", "instagram", "linkedin",
                  "is_featured", "is_active", "order"]


class FAQForm(StyledModelForm):
    class Meta:
        model = FAQ
        fields = ["question", "answer", "category", "is_active", "order"]


class TestimonialForm(StyledModelForm):
    class Meta:
        model = Testimonial
        fields = ["author_name", "author_role", "quote", "rating", "photo", "event_type",
                  "location", "is_featured", "is_active", "order"]


class ContactMessageForm(StyledModelForm):
    class Meta:
        model = ContactMessage
        fields = ["status", "internal_notes"]


class WebsiteSettingsForm(StyledModelForm):
    class Meta:
        model = WebsiteSettings
        exclude = ["created_at", "updated_at"]


class SEOSettingsForm(StyledModelForm):
    class Meta:
        model = SEOSettings
        exclude = ["created_at", "updated_at"]


class AlbumRequestForm(StyledModelForm):
    class Meta:
        model = AlbumRequest
        fields = ["title", "album_type", "size", "cover_material", "page_count",
                  "status", "due_date", "price", "admin_notes"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}