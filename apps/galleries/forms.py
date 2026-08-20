from django import forms

FIELD_CLASS = (
    "w-full rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-sm text-white "
    "placeholder-white/40 outline-none transition focus:border-gold focus:ring-2 focus:ring-gold/30"
)


class GalleryAccessForm(forms.Form):
    """Access-code gate for link-shared galleries."""

    access_code = forms.CharField(
        max_length=16,
        label="Access code",
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CLASS + " uppercase tracking-[0.3em]",
                "placeholder": "XXXXXXXX",
                "autocomplete": "off",
                "autocapitalize": "characters",
            }
        ),
    )

    def __init__(self, *args, gallery=None, **kwargs):
        self.gallery = gallery
        super().__init__(*args, **kwargs)

    def clean_access_code(self):
        code = (self.cleaned_data.get("access_code") or "").strip().upper()
        if self.gallery and code != (self.gallery.access_code or "").upper():
            raise forms.ValidationError("That access code is not valid for this gallery.")
        return code


class SelectionSubmitForm(forms.Form):
    """Final step when a client sends their picks to the studio."""

    ALBUM_CHOICES = [
        ("fine_art", "Fine art album"),
        ("layflat", "Layflat album"),
        ("storybook", "Storybook"),
        ("print_box", "Print box"),
        ("digital", "Digital delivery only"),
    ]

    album_type = forms.ChoiceField(
        choices=ALBUM_CHOICES,
        required=False,
        initial="fine_art",
        widget=forms.Select(attrs={"class": FIELD_CLASS}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": FIELD_CLASS,
                "rows": 4,
                "placeholder": "Anything we should know about your picks?",
            }
        ),
    )