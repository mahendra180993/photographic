from django import forms

from apps.cms.models import ContactMessage

FIELD_CLASS = (
    "w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-paper "
    "placeholder-paper/40 outline-none transition focus:border-gold focus:ring-2 focus:ring-gold/20"
)


class ContactForm(forms.ModelForm):
    # Simple honeypot - real visitors never see or fill this field.
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    consent = forms.BooleanField(
        required=True,
        label="I agree to be contacted about my enquiry.",
    )

    class Meta:
        model = ContactMessage
        fields = [
            "name",
            "email",
            "phone",
            "event_type",
            "event_date",
            "location",
            "budget",
            "subject",
            "message",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "name": "Your full name",
            "email": "you@example.com",
            "phone": "+33 6 00 00 00 00",
            "event_type": "Wedding, editorial, brand...",
            "location": "Paris, Lake Como, remote...",
            "budget": "Approximate budget",
            "subject": "What is this about?",
            "message": "Tell us about your story, dates and vision.",
        }
        for name, field in self.fields.items():
            if name in {"website", "consent"}:
                continue
            field.widget.attrs.setdefault("class", FIELD_CLASS)
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])
        self.fields["consent"].widget.attrs.update(
            {"class": "mt-1 h-4 w-4 rounded border-white/20 bg-transparent text-gold focus:ring-gold"}
        )
        self.fields["phone"].required = False
        self.fields["subject"].required = False

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value:
            raise forms.ValidationError("Spam detected.")
        return value