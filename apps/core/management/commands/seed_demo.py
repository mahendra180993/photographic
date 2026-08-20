"""
Seed the platform with a complete, browsable demo dataset.

    python manage.py seed_demo
    python manage.py seed_demo --reset            # wipe demo content and rebuild
    python manage.py seed_demo --refresh-images   # keep data, re-download imagery
    python manage.py seed_demo --no-images        # skip imagery entirely (offline)

Photographs are real images downloaded from the Unsplash CDN so the demo looks
like a working studio rather than a wireframe. An internet connection is
therefore required unless you pass --no-images. A download that fails degrades
to a Pillow placeholder instead of aborting, so the seed always completes.

Creates the admin login `admin / admin123` plus photographers, customers,
galleries, portfolio, services, testimonials, team members, FAQs and website
settings.
"""

import io
import random
import urllib.request
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.albums.models import AlbumRequest, AlbumSelection
from apps.analytics.models import ActivityLog
from apps.cms.models import FAQ, ContactMessage, SEOSettings, TeamMember, Testimonial, WebsiteSettings
from apps.customers.models import Customer, Photographer
from apps.galleries.models import Gallery, GalleryAccessLog, GalleryCategory, GalleryImage
from apps.notifications.models import Notification
from apps.portfolio.models import PortfolioCategory, PortfolioImage
from apps.services.models import Service

User = get_user_model()

# Curated real photography from the Unsplash CDN, grouped by the theme each part
# of the demo needs. Sizing query parameters are appended by fetch_photo().
PHOTOS = {
    "weddings": [
        "https://images.unsplash.com/photo-1519741497674-611481863552",
        "https://images.unsplash.com/photo-1511285560929-80b456fea0bc",
        "https://images.unsplash.com/photo-1465495976277-4387d4b0b4c6",
        "https://images.unsplash.com/photo-1519225421980-715cb0215aed",
        "https://images.unsplash.com/photo-1523438885200-e635ba2c371e",
        "https://images.unsplash.com/photo-1522673607200-164d1b6ce486",
        "https://images.unsplash.com/photo-1520854221256-17451cc331bf",
        "https://images.unsplash.com/photo-1507504031003-b417219a0fde",
        "https://images.unsplash.com/photo-1591604466107-ec97de577aff",
        "https://images.unsplash.com/photo-1606216794074-735e91aa2c92",
        "https://images.unsplash.com/photo-1583939003579-730e3918a45a",
        "https://images.unsplash.com/photo-1460978812857-470ed1c77af0",
        "https://images.unsplash.com/photo-1478146896981-b80fe463b330",
        "https://images.unsplash.com/photo-1469371670807-013ccf25f16a",
        "https://images.unsplash.com/photo-1546032996-6dfacbacbf3f",
        "https://images.unsplash.com/photo-1550005809-91ad75fb315f",
        "https://images.unsplash.com/photo-1537633552985-df8429e8048b",
        "https://images.unsplash.com/photo-1511578314322-379afb476865",
    ],
    "editorial": [
        "https://images.unsplash.com/photo-1483985988355-763728e1935b",
        "https://images.unsplash.com/photo-1490481651871-ab68de25d43d",
        "https://images.unsplash.com/photo-1469334031218-e382a71b716b",
        "https://images.unsplash.com/photo-1509319117193-57bab727e09d",
        "https://images.unsplash.com/photo-1441984904996-e0b6ba687e04",
        "https://images.unsplash.com/photo-1487222477894-8943e31ef7b2",
        "https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b",
        "https://images.unsplash.com/photo-1529139574466-a303027c1d8b",
        "https://images.unsplash.com/photo-1485231183945-fffde7cc051e",
        "https://images.unsplash.com/photo-1496747611176-843222e1e57c",
    ],
    "portraits": [
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330",
        "https://images.unsplash.com/photo-1438761681033-6461ffad8d80",
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2",
        "https://images.unsplash.com/photo-1524504388940-b1c1722653e1",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9",
        "https://images.unsplash.com/photo-1489424731084-a5d8b219a5bb",
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d",
        "https://images.unsplash.com/photo-1517070208541-6ddc4d3efbcb",
        "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04",
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb",
        "https://images.unsplash.com/photo-1521119989659-a83eee488004",
        "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453",
    ],
    "interiors": [
        "https://images.unsplash.com/photo-1493809842364-78817add7ffb",
        "https://images.unsplash.com/photo-1586023492125-27b2c045efd7",
        "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267",
        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2",
        "https://images.unsplash.com/photo-1502005229762-cf1b2da7c5d6",
        "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c",
        "https://images.unsplash.com/photo-1524758631624-e2822e304c36",
        "https://images.unsplash.com/photo-1567767292278-a4f21aa2d36e",
    ],
    "landscape": [
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05",
        "https://images.unsplash.com/photo-1439853949127-fa647821eba0",
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470",
        "https://images.unsplash.com/photo-1472214103451-9374bd1c798e",
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e",
        "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d",
        "https://images.unsplash.com/photo-1433086966358-54859d0ed716",
        "https://images.unsplash.com/photo-1418065460487-3e41a6c84dc5",
    ],
    "commercial": [
        "https://images.unsplash.com/photo-1566073771259-6a8506099945",
        "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9",
        "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa",
        "https://images.unsplash.com/photo-1445019980597-93fa8acb246c",
        "https://images.unsplash.com/photo-1564501049412-61c2a3083791",
        "https://images.unsplash.com/photo-1590490360182-c33d57733427",
        "https://images.unsplash.com/photo-1578683010236-d716f9a3f461",
        "https://images.unsplash.com/photo-1618773928121-c32242e63f39",
        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b",
        "https://images.unsplash.com/photo-1611892440504-42a792e24d32",
    ],
    "hero": [
        "https://images.unsplash.com/photo-1519741497674-611481863552",
        "https://images.unsplash.com/photo-1502920917128-1aa500764cbd",
        "https://images.unsplash.com/photo-1452587925148-ce544e77e70d",
        "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429",
        "https://images.unsplash.com/photo-1516035069371-29a1b244cc32",
    ],
    "team": [
        "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e",
        "https://images.unsplash.com/photo-1560250097-0b93528c311a",
        "https://images.unsplash.com/photo-1580489944761-15a19d654956",
        "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e",
        "https://images.unsplash.com/photo-1519345182560-3f2917c472ef",
        "https://images.unsplash.com/photo-1607746882042-944635dfe10e",
        "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91",
        "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f",
    ],
    "about": [
        "https://images.unsplash.com/photo-1554048612-b6a482bc67e5",
        "https://images.unsplash.com/photo-1542038784456-1ea8e935640e",
        "https://images.unsplash.com/photo-1516724562728-afc824a36e84",
        "https://images.unsplash.com/photo-1493863641943-9b68992a8d07",
        "https://images.unsplash.com/photo-1471341971476-ae15ff5dd4ea",
    ],
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DOWNLOAD_STATS = {"downloaded": 0, "reused": 0, "failed": 0}
DOWNLOAD_FAILURES = []

_PAYLOAD_CACHE = {}
_THEME_CURSORS = {}

PALETTES = [
    ((28, 30, 36), (120, 108, 92)),
    ((236, 231, 222), (176, 158, 130)),
    ((44, 40, 38), (196, 169, 129)),
    ((214, 208, 199), (94, 96, 104)),
    ((18, 20, 24), (86, 96, 110)),
    ((240, 236, 229), (200, 169, 81)),
]


def pick(theme, offset=None):
    """Return a URL from a theme pool, advancing a per-theme cursor by default."""
    pool = PHOTOS[theme]
    if offset is None:
        offset = _THEME_CURSORS.get(theme, 0)
        _THEME_CURSORS[theme] = offset + 1
    return pool[offset % len(pool)]


def build_placeholder(width, height, seed, label=""):
    """Offline fallback used only when a download fails."""
    from PIL import Image, ImageDraw, ImageFilter

    rng = random.Random(seed)
    top, bottom = PALETTES[seed % len(PALETTES)]

    gradient = Image.linear_gradient("L").resize((width, height))
    base = Image.composite(
        Image.new("RGB", (width, height), bottom),
        Image.new("RGB", (width, height), top),
        gradient,
    )

    overlay = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(6):
        radius = rng.randint(int(width * 0.2), int(width * 0.8))
        cx = rng.randint(0, width)
        cy = rng.randint(0, height)
        tone = rng.randint(40, 220)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(tone, tone, tone))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(1, width // 8)))
    base = Image.blend(base, overlay, 0.28)

    grain = Image.effect_noise((width, height), 12).convert("L")
    base = Image.blend(base, Image.merge("RGB", (grain, grain, grain)), 0.06)

    if label:
        ImageDraw.Draw(base).text((28, height - 42), label[:48].upper(), fill=(255, 255, 255))

    buffer = io.BytesIO()
    base.save(buffer, format="JPEG", quality=80, optimize=True)
    buffer.seek(0)
    return ContentFile(buffer.read())


def fetch_photo(url, width=1400, label=""):
    """Download a real photograph and return it as a JPEG ContentFile."""
    cache_key = (url, width)
    if cache_key in _PAYLOAD_CACHE:
        DOWNLOAD_STATS["reused"] += 1
        return ContentFile(_PAYLOAD_CACHE[cache_key])

    target = url if "?" in url else f"{url}?auto=format&fit=crop&w={width}&q=80"
    request = urllib.request.Request(
        target, headers={"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/jpeg,*/*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
        if len(payload) < 2048:
            raise ValueError(f"suspiciously small response ({len(payload)} bytes)")
    except Exception as exc:  # noqa: BLE001 - any network fault must stay non-fatal
        DOWNLOAD_STATS["failed"] += 1
        DOWNLOAD_FAILURES.append(f"{target} -> {exc}")
        return build_placeholder(width, max(1, int(width * 0.68)), abs(hash(url)) % 991, label)

    _PAYLOAD_CACHE[cache_key] = payload
    DOWNLOAD_STATS["downloaded"] += 1
    return ContentFile(payload)


class Command(BaseCommand):
    help = "Populate the database with a rich demo dataset for Lumina Atelier."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo content first.")
        parser.add_argument("--no-images", action="store_true", help="Skip photographs entirely (works offline).")
        parser.add_argument(
            "--refresh-images",
            action="store_true",
            help="Re-download photographs for content that already exists, replacing old files.",
        )

    def handle(self, *args, **options):
        self.with_images = not options["no_images"]
        # A reset leaves the settings singletons behind, so treat it as a refresh too.
        self.refresh_images = options["refresh_images"] or options["reset"]
        if options["reset"]:
            self.reset()

        with transaction.atomic():
            self.stdout.write(self.style.MIGRATE_HEADING("Seeding Lumina Atelier demo data"))
            if self.with_images:
                self.stdout.write("  downloading photographs from the Unsplash CDN, this takes a few minutes...")
            admin = self.create_users()
            photographers = self.create_photographers()
            self.create_settings()
            self.create_services()
            self.create_team()
            self.create_faqs()
            self.create_testimonials()
            portfolio = self.create_portfolio()
            customers = self.create_customers(admin, photographers)
            galleries = self.create_galleries(admin, customers, photographers)
            self.create_engagement(customers, galleries)
            self.create_messages()
            self.create_activity(admin, galleries)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("  Studio admin   : admin / admin123        -> /studio/")
        self.stdout.write("  Photographer   : elise / studio123       -> /studio/")
        self.stdout.write("  Client login   : client / client123      -> /client/")
        self.stdout.write("  Second client  : marchetti / client123   -> /client/")
        self.stdout.write(f"  Portfolio collections: {len(portfolio)}   Galleries: {len(galleries)}")
        if self.with_images:
            self.stdout.write(
                "  Photographs: {downloaded} downloaded, {reused} reused, {failed} fell back to placeholders".format(
                    **DOWNLOAD_STATS
                )
            )
            for failure in DOWNLOAD_FAILURES[:10]:
                self.stdout.write(self.style.WARNING(f"    ! {failure}"))
            if len(DOWNLOAD_FAILURES) > 10:
                self.stdout.write(self.style.WARNING(f"    ! ...and {len(DOWNLOAD_FAILURES) - 10} more"))

    # -- helpers ---------------------------------------------------------
    def log(self, message):
        self.stdout.write(f"  - {message}")

    def apply_image(self, obj, field_name, url, filename, width=1400, save=True):
        """Attach a downloaded photograph, honouring --no-images and --refresh-images."""
        if not self.with_images:
            return False
        field = getattr(obj, field_name)
        if field and not self.refresh_images:
            return False
        if field:
            field.delete(save=False)
        field.save(filename, fetch_photo(url, width, filename), save=save)
        return True

    def reset(self):
        self.stdout.write(self.style.WARNING("Removing existing demo content..."))
        AlbumSelection.objects.all().delete()
        AlbumRequest.objects.all().delete()
        GalleryAccessLog.objects.all().delete()
        GalleryImage.objects.all().delete()
        Gallery.objects.all().delete()
        GalleryCategory.objects.all().delete()
        PortfolioImage.objects.all().delete()
        PortfolioCategory.objects.all().delete()
        Customer.objects.all().delete()
        Photographer.objects.all().delete()
        Service.objects.all().delete()
        Testimonial.objects.all().delete()
        TeamMember.objects.all().delete()
        FAQ.objects.all().delete()
        ContactMessage.objects.all().delete()
        Notification.objects.all().delete()
        ActivityLog.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

    # -- users -----------------------------------------------------------
    def create_users(self):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@luminaatelier.test",
                "first_name": "Amara",
                "last_name": "Vance",
                "role": User.Roles.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "email_verified": True,
            },
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.role = User.Roles.ADMIN
        admin.save()
        self.log(f"admin user {'created' if created else 'updated'} (admin / admin123)")
        return admin

    def create_photographers(self):
        specs = [
            {
                "username": "elise",
                "first_name": "Elise",
                "last_name": "Marchand",
                "display_name": "Elise Marchand",
                "title": "Founder & lead photographer",
                "specialties": "Weddings, Fine art, Film",
                "bio": "Elise founded the atelier in 2013 after a decade in editorial. She shoots "
                       "medium-format film alongside digital and is happiest in soft northern light.",
                "is_lead": True,
            },
            {
                "username": "tobias",
                "first_name": "Tobias",
                "last_name": "Reine",
                "display_name": "Tobias Reine",
                "title": "Editorial & brand photographer",
                "specialties": "Editorial, Brand, Architecture",
                "bio": "Tobias brings a graphic, architectural eye to campaigns and interiors, with a "
                       "background in industrial design.",
                "is_lead": False,
            },
        ]
        photographers = []
        for index, spec in enumerate(specs):
            user, _ = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": f"{spec['username']}@luminaatelier.test",
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "role": User.Roles.PHOTOGRAPHER,
                    "is_staff": True,
                },
            )
            user.set_password("studio123")
            user.role = User.Roles.PHOTOGRAPHER
            user.is_staff = True
            user.save()

            photographer, _ = Photographer.objects.get_or_create(
                slug=slugify(spec["display_name"]),
                defaults={
                    "user": user,
                    "display_name": spec["display_name"],
                    "title": spec["title"],
                    "bio": spec["bio"],
                    "specialties": spec["specialties"],
                    "email": user.email,
                    "phone": "+33 1 84 80 00 0" + str(index + 1),
                    "is_lead": spec["is_lead"],
                    "order": index,
                },
            )
            self.apply_image(
                photographer, "avatar", pick("team"), f"{photographer.slug}-avatar.jpg", width=900
            )
            photographers.append(photographer)
        self.log(f"{len(photographers)} photographers")
        return photographers

    # -- CMS ---------------------------------------------------------------
    def create_settings(self):
        site = WebsiteSettings.load()
        site.site_name = "Lumina Atelier"
        site.tagline = "Photography for the quietly extraordinary"
        site.hero_eyebrow = "Fine art photography atelier - Paris"
        site.hero_title = "Light, held still."
        site.hero_subtitle = (
            "A boutique studio crafting timeless imagery for weddings, editorial and brands. "
            "Twelve commissions a year, each one treated as an heirloom."
        )
        site.hero_cta_label = "View the portfolio"
        site.about_title = "An atelier, not a factory"
        site.about_intro = (
            "We believe a photograph should feel like a memory rather than a record - warm, "
            "unhurried and honest."
        )
        site.about_body = (
            "Founded in Paris in 2013, Lumina Atelier is a two-photographer studio supported by a "
            "small team of retouchers and album makers. We shoot on medium-format film and digital, "
            "we travel worldwide, and we deliver through a private client gallery designed to be as "
            "considered as the images inside it."
        )
        site.email = "studio@luminaatelier.test"
        site.booking_email = "bookings@luminaatelier.test"
        site.phone = "+33 1 84 80 00 00"
        site.address = "18 Rue des Lumieres"
        site.postcode = "75003"
        site.city = "Paris"
        site.country = "France"
        site.opening_hours = "Mon - Fri, 09:00 - 18:00 CET"
        site.instagram = "https://instagram.com/"
        site.pinterest = "https://pinterest.com/"
        site.vimeo = "https://vimeo.com/"
        site.years_experience = 12
        site.projects_delivered = 486
        site.awards_count = 17
        site.countries_count = 23
        site.footer_note = "Crafted with care in Paris."
        site.announcement = "Now booking 2026 commissions - a handful of dates remain."
        site.announcement_active = True
        site.accent_color = "#D4AF37"
        site.save()

        hero_url = pick("hero", offset=0)
        self.apply_image(site, "hero_image", hero_url, "hero.jpg", width=2000)
        self.apply_image(site, "about_image", pick("about"), "about.jpg", width=1600)

        seo = SEOSettings.load()
        seo.meta_title = "Lumina Atelier | Fine Art Wedding & Editorial Photography, Paris"
        seo.meta_description = (
            "Lumina Atelier is a boutique Paris photography studio creating timeless wedding, "
            "editorial and brand imagery worldwide. Private client galleries included."
        )
        seo.meta_keywords = (
            "paris wedding photographer, fine art photography, editorial photographer, "
            "destination wedding, brand photography studio"
        )
        seo.canonical_domain = "http://localhost:8000"
        seo.save()
        # The share card reuses the hero frame, served from the download cache.
        self.apply_image(seo, "og_image", hero_url, "og-image.jpg", width=2000)
        self.log("website + SEO settings")
    def create_services(self):
        data = [
            {
                "title": "Wedding Photography",
                "tagline": "A full day, quietly observed",
                "short_description": "Documentary-led coverage of your wedding day, from first light to last dance.",
                "description": "Two photographers, unhurried direction and a gentle presence. We plan the day with "
                               "you in advance, then step back and let it unfold - stepping in only for the portraits "
                               "you will want on the wall in thirty years.",
                "price_from": 4800,
                "duration": "Up to 12 hours",
                "turnaround": "6 weeks",
                "icon": "ring",
                "features": "Two photographers\nPre-wedding consultation\n600+ edited photographs\n"
                            "Private online gallery for one year\nFine art album consultation\nWorldwide travel",
                "deliverables": "Private client gallery\nHigh-resolution downloads\nPrint release\nSocial preview set",
                "is_featured": True,
            },
            {
                "title": "Editorial & Campaign",
                "tagline": "Imagery with a point of view",
                "short_description": "Commissioned editorial and campaign photography for magazines and brands.",
                "description": "From concept boards to final grade, we produce cohesive editorial stories with an "
                               "art-directed eye. Studio or location, crew supplied as needed.",
                "price_from": 2400,
                "duration": "Half or full day",
                "turnaround": "2 weeks",
                "icon": "film",
                "features": "Art direction\nStudio or location\nCrew and casting support\nSame-day selects\n"
                            "Full commercial licensing",
                "deliverables": "Selects gallery within 24h\nRetouched masters\nLicensing agreement",
                "is_featured": True,
            },
            {
                "title": "Portraiture",
                "tagline": "Considered, unhurried, yours",
                "short_description": "Studio and environmental portraits for individuals, families and founders.",
                "description": "A calm ninety minutes, natural light, and a handful of frames you will actually love. "
                               "Ideal for founders, authors, families and milestone portraits.",
                "price_from": 850,
                "duration": "90 minutes",
                "turnaround": "10 days",
                "icon": "camera",
                "features": "Pre-shoot styling notes\n40+ edited photographs\nStudio or location\nPrint credit included",
                "deliverables": "Private gallery\nWeb and print resolutions",
            },
            {
                "title": "Brand & Interiors",
                "tagline": "Spaces and the people in them",
                "short_description": "Hospitality, interiors and product imagery for brands that care about detail.",
                "description": "Architectural discipline with a warm, human finish. We build shot lists with your "
                               "team and deliver a library you can use for a year.",
                "price_from": 1800,
                "duration": "Full day",
                "turnaround": "3 weeks",
                "icon": "building",
                "features": "Shot-list planning\nOn-set styling\n120+ library images\n12-month licence",
                "deliverables": "Asset library\nCropped social set\nUsage guide",
            },
            {
                "title": "Fine Art Albums",
                "tagline": "The heirloom object",
                "short_description": "Hand-bound albums and archival prints produced in a small Italian bindery.",
                "description": "Choose your frames in the client gallery and we design the layout, refine it with you, "
                               "then produce it in linen, silk or leather with archival inks.",
                "price_from": 690,
                "duration": "4 weeks production",
                "turnaround": "4 weeks",
                "icon": "book",
                "features": "Layout designed by the studio\nTwo revision rounds\nLinen, silk or leather\n"
                            "Archival pigment printing\nPresentation box",
                "deliverables": "Hand-bound album\nDigital layout proof",
            },
        ]
        themes = ["weddings", "editorial", "portraits", "interiors", "about"]
        for index, spec in enumerate(data):
            service, _ = Service.objects.get_or_create(
                title=spec["title"],
                defaults={**spec, "order": index, "currency": "EUR"},
            )
            self.apply_image(service, "image", pick(themes[index]), f"{service.slug}.jpg", width=1600)
        self.log(f"{len(data)} services")

    def create_team(self):
        data = [
            ("Amara Vance", "Studio director", "Amara keeps the atelier running - schedules, contracts and the "
                                               "occasional second shooter shift."),
            ("Elise Marchand", "Founder & lead photographer", "Elise founded the studio in 2013 and shoots most "
                                                              "weddings alongside her film camera."),
            ("Tobias Reine", "Editorial photographer", "Tobias leads brand and interiors work with a graphic, "
                                                       "architectural eye."),
            ("Noor Haddad", "Retoucher & album designer", "Noor hand-finishes every frame and designs the albums "
                                                          "produced in our Italian bindery."),
        ]
        for index, (name, role, bio) in enumerate(data):
            member, _ = TeamMember.objects.get_or_create(
                name=name, defaults={"role": role, "bio": bio, "order": index}
            )
            self.apply_image(member, "photo", pick("team"), f"{member.slug}.jpg", width=1200)
        self.log(f"{len(data)} team members")

    def create_faqs(self):
        data = [
            ("How far in advance should we book?", "Most couples book nine to fourteen months ahead. We take a "
             "maximum of twelve weddings a year, so popular dates go early - but do ask, we occasionally have "
             "late availability.", "booking"),
            ("Do you travel?", "Always. Roughly a third of our work is outside France. Travel and accommodation "
             "are quoted transparently at cost.", "booking"),
            ("How many photographs will we receive?", "A full wedding day typically yields 600 to 900 edited "
             "photographs. Portrait sessions deliver 40 or more.", "delivery"),
            ("How do we see our photographs?", "You receive a private client gallery on this website. Sign in to "
             "view, mark favourites, select for your album and download the originals.", "delivery"),
            ("How long is our gallery available?", "Twelve months as standard, and we never delete an archive - "
             "email us any time and we will reopen it.", "delivery"),
            ("Can we share the gallery with family?", "Yes. We can switch your gallery to a shareable link with an "
             "access code so relatives can browse without your login.", "delivery"),
            ("What is your payment schedule?", "A 30% retainer secures the date, with the balance due two weeks "
             "before the shoot. Albums are invoiced separately.", "pricing"),
            ("Do you shoot film?", "Yes - most weddings include a medium-format film component, blended with "
             "digital coverage at no extra cost.", "general"),
        ]
        for index, (question, answer, category) in enumerate(data):
            FAQ.objects.get_or_create(
                question=question, defaults={"answer": answer, "category": category, "order": index}
            )
        self.log(f"{len(data)} FAQs")

    def create_testimonials(self):
        data = [
            ("Juliette & Marc", "Wedding, Provence", "We forgot there was a photographer there at all - and then the "
             "gallery arrived and we cried for an hour. Every frame feels like the day actually felt.", 5, True),
            ("Camille Rousseau", "Editor, MAISON magazine", "Tobias delivered a twelve-page story on a two-day "
             "schedule with a calm that made the whole crew better. The selects were live within a day.", 5, True),
            ("Idris & Amara", "Wedding, Lake Como", "The client gallery alone was worth it. Choosing our album photos "
             "took an evening instead of a month.", 5, True),
            ("Hotel Verano", "Brand & interiors", "Our booking rate lifted measurably after the new imagery went "
             "live. Elegant, warm, and exactly on brief.", 5, False),
            ("Sofia Lindqvist", "Portrait session", "I hate being photographed and somehow ended up with a portrait "
             "I now use everywhere.", 5, False),
            ("The Ashford Family", "Family portraits", "Three generations, one very small child, and not a single "
             "forced smile in the whole set.", 5, False),
        ]
        for index, (name, role, quote, rating, featured) in enumerate(data):
            testimonial, _ = Testimonial.objects.get_or_create(
                author_name=name,
                quote=quote,
                defaults={"author_role": role, "rating": rating, "is_featured": featured, "order": index},
            )
            self.apply_image(
                testimonial, "photo", pick("portraits"), f"{slugify(name)}.jpg", width=900
            )
        self.log(f"{len(data)} testimonials")
    # -- portfolio ----------------------------------------------------------
    def create_portfolio(self):
        data = [
            ("Weddings", "Unhurried documentary coverage", 8, "weddings"),
            ("Editorial", "Stories for magazines and brands", 6, "editorial"),
            ("Portraiture", "Founders, families and friends", 6, "portraits"),
            ("Interiors", "Hotels, restaurants and homes", 5, "interiors"),
            ("Landscape", "Personal work from the road", 5, "landscape"),
        ]
        categories = []
        for index, (name, subtitle, count, theme) in enumerate(data):
            category, _ = PortfolioCategory.objects.get_or_create(
                name=name,
                defaults={
                    "subtitle": subtitle,
                    "description": f"A selection of {name.lower()} work from the Lumina Atelier archive.",
                    "is_featured": index < 3,
                    "order": index,
                },
            )
            categories.append(category)
            if not self.with_images:
                continue

            if category.images.exists():
                if not self.refresh_images:
                    continue
                for existing in category.images.all():
                    existing.image.delete(save=False)
                category.images.all().delete()

            self.apply_image(category, "cover_image", pick(theme), f"{category.slug}-cover.jpg", width=1800)
            for position in range(count):
                image = PortfolioImage(
                    category=category,
                    title=f"{name} no. {position + 1:02d}",
                    caption=f"From the {name.lower()} archive.",
                    location=["Paris", "Provence", "Lake Como", "Copenhagen", "Marrakech"][position % 5],
                    order=position,
                    is_featured=position < 2,
                )
                image.image.save(
                    f"{category.slug}-{position + 1}.jpg",
                    fetch_photo(pick(theme), 1400, f"{name} {position + 1:02d}"),
                    save=False,
                )
                image.save()
        self.log(f"{len(categories)} portfolio collections")
        return categories

    # -- customers & galleries ---------------------------------------------
    def create_customers(self, admin, photographers):
        data = [
            ("Juliette Bernard", "juliette@example.com", "couple", "client", "client123", "Paris", "France"),
            ("Marco Marchetti", "marco@example.com", "couple", "marchetti", "client123", "Como", "Italy"),
            ("Hotel Verano", "studio@hotelverano.example", "corporate", None, None, "Lisbon", "Portugal"),
            ("Sofia Lindqvist", "sofia@example.com", "individual", None, None, "Stockholm", "Sweden"),
        ]
        customers = []
        for index, (name, email, kind, username, password, city, country) in enumerate(data):
            user = None
            if username:
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": name.split(" ")[0],
                        "last_name": " ".join(name.split(" ")[1:]),
                        "role": User.Roles.CLIENT,
                    },
                )
                user.set_password(password)
                user.role = User.Roles.CLIENT
                user.save()

            customer, _ = Customer.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": name,
                    "user": user,
                    "customer_type": kind,
                    "status": Customer.Status.ACTIVE,
                    "city": city,
                    "country": country,
                    "phone": f"+33 6 12 34 56 {index:02d}",
                    "assigned_photographer": photographers[index % len(photographers)],
                    "created_by": admin,
                    "tags": "vip, referral" if index == 0 else "",
                    "notes": "Prefers film-heavy coverage." if index == 0 else "",
                },
            )
            if customer.user_id is None and user is not None:
                customer.user = user
                customer.save(update_fields=["user"])
            customers.append(customer)
        self.log(f"{len(customers)} customers")
        return customers

    def create_galleries(self, admin, customers, photographers):
        now = timezone.now()
        categories = {}
        for index, name in enumerate(["Weddings", "Editorial", "Portraits", "Commercial"]):
            categories[name], _ = GalleryCategory.objects.get_or_create(name=name, defaults={"order": index})

        specs = [
            {
                "title": "Juliette & Marc - Chateau de Vaux",
                "customer": customers[0],
                "category": categories["Weddings"],
                "status": Gallery.Status.DELIVERED,
                "visibility": Gallery.Visibility.PRIVATE,
                "location": "Provence, France",
                "images": 16,
                "theme": "weddings",
                "welcome": "Your wedding gallery is ready. Mark your favourites, then submit your album "
                           "selection whenever you are ready - there is no rush.",
                "selection_limit": 40,
                "expires_in": 240,
            },
            {
                "title": "Marchetti Wedding - Lake Como",
                "customer": customers[1],
                "category": categories["Weddings"],
                "status": Gallery.Status.READY,
                "visibility": Gallery.Visibility.CODE,
                "location": "Lake Como, Italy",
                "images": 12,
                "theme": "weddings",
                "welcome": "A first look at your weekend by the lake. Share the link and code with family.",
                "selection_limit": 0,
                "expires_in": 120,
            },
            {
                "title": "Hotel Verano - Brand Library",
                "customer": customers[2],
                "category": categories["Commercial"],
                "status": Gallery.Status.DELIVERED,
                "visibility": Gallery.Visibility.PRIVATE,
                "location": "Lisbon, Portugal",
                "images": 10,
                "theme": "commercial",
                "welcome": "Your 12-month image library. Downloads are enabled for your marketing team.",
                "selection_limit": 0,
                "expires_in": 365,
            },
            {
                "title": "Sofia Lindqvist - Studio Portraits",
                "customer": customers[3],
                "category": categories["Portraits"],
                "status": Gallery.Status.DRAFT,
                "visibility": Gallery.Visibility.PRIVATE,
                "location": "Stockholm, Sweden",
                "images": 8,
                "theme": "portraits",
                "welcome": "",
                "selection_limit": 10,
                "expires_in": 90,
            },
        ]

        galleries = []
        for index, spec in enumerate(specs):
            gallery, _ = Gallery.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "customer": spec["customer"],
                    "photographer": photographers[index % len(photographers)],
                    "category": spec["category"],
                    "description": "Delivered by Lumina Atelier.",
                    "welcome_message": spec["welcome"],
                    "location": spec["location"],
                    "event_date": (now - timedelta(days=30 * (index + 1))).date(),
                    "status": spec["status"],
                    "visibility": spec["visibility"],
                    "expires_at": now + timedelta(days=spec["expires_in"]),
                    "selection_limit": spec["selection_limit"],
                    "allow_downloads": index != 1,
                    "watermark_enabled": index == 1,
                    "created_by": admin,
                    "view_count": (4 - index) * 17,
                },
            )
            galleries.append(gallery)

            if not self.with_images:
                continue

            if gallery.images.exists():
                if not self.refresh_images:
                    continue
                # The cover points at the same stored file as its GalleryImage,
                # so clear the reference and let the image rows delete the files.
                gallery.cover_image = None
                gallery.save(update_fields=["cover_image"])
                for existing in gallery.images.all():
                    existing.image.delete(save=False)
                gallery.images.all().delete()

            # A commercial library mixes rooms with the interiors that sell them.
            themes = [spec["theme"]] if spec["theme"] != "commercial" else ["commercial", "interiors"]
            for position in range(spec["images"]):
                image = GalleryImage(
                    gallery=gallery,
                    title=f"Frame {position + 1:03d}",
                    order=position,
                    uploaded_by=admin,
                    is_highlight=position < 3,
                )
                image.image.save(
                    f"{gallery.slug}-{position + 1:03d}.jpg",
                    fetch_photo(
                        pick(themes[position % len(themes)]),
                        1400,
                        f"{gallery.slug} {position + 1:03d}",
                    ),
                    save=False,
                )
                image.save()

            first = gallery.images.order_by("order").first()
            if first:
                first.is_cover = True
                first.save(update_fields=["is_cover"])
                gallery.cover_image = first.image
                gallery.save(update_fields=["cover_image"])

        self.log(f"{len(galleries)} galleries with photographs")
        return galleries
    def create_engagement(self, customers, galleries):
        """Add realistic selections, an album request and access history."""
        gallery = galleries[0]
        customer = customers[0]
        images = list(gallery.images.order_by("order")[:6])
        if not images:
            return

        album, _ = AlbumRequest.objects.get_or_create(
            gallery=gallery,
            customer=customer,
            defaults={
                "title": f"{gallery.title} - album selection",
                "album_type": AlbumRequest.AlbumType.FINE_ART,
                "size": "30x30 cm",
                "cover_material": "Oatmeal linen",
                "page_count": 40,
                "notes": "Please keep the ceremony sequence in order, and include the portrait by the olive tree.",
                "status": AlbumRequest.Status.DRAFT,
            },
        )
        for position, image in enumerate(images):
            AlbumSelection.objects.get_or_create(
                gallery=gallery,
                image=image,
                customer=customer,
                defaults={"album_request": album, "is_selected": True, "sequence": position},
            )
        # Submit only once the picks exist so the notification reports a real count.
        if album.status == AlbumRequest.Status.DRAFT:
            album.submitted_at = timezone.now() - timedelta(days=3)
            album.mark_submitted()

        for action in ["view", "select", "submit", "download"]:
            GalleryAccessLog.objects.get_or_create(
                gallery=gallery,
                action=action,
                defaults={"user": customer.user, "ip_address": "127.0.0.1", "note": "seeded"},
            )

        if customer.user_id:
            Notification.objects.get_or_create(
                recipient=customer.user,
                title="Your gallery is ready",
                defaults={
                    "message": f"'{gallery.title}' is available in your private client area.",
                    "category": Notification.Category.GALLERY,
                    "level": Notification.Level.SUCCESS,
                    "url": gallery.get_absolute_url(),
                    "related_gallery": gallery,
                },
            )
        self.log("client selections, album request and access history")

    def create_messages(self):
        data = [
            ("Helena Fischer", "helena@example.com", "Wedding enquiry - June 2026",
             "We are getting married near Annecy next June and love your film work. Are you free on the 13th?",
             "Wedding", "new"),
            ("Studio Nord", "hello@studionord.example", "Campaign shoot - autumn",
             "We are planning a five-day campaign across Copenhagen and Malmo. Could you send rates?",
             "Brand", "read"),
            ("Priya Nair", "priya@example.com", "Family portraits",
             "Three generations visiting Paris in October - would love an outdoor session.",
             "Portrait", "replied"),
        ]
        for name, email, subject, message, event_type, status in data:
            ContactMessage.objects.get_or_create(
                email=email,
                subject=subject,
                defaults={
                    "name": name,
                    "message": message,
                    "event_type": event_type,
                    "status": status,
                    "source": "website",
                },
            )
        self.log(f"{len(data)} enquiries")

    def create_activity(self, admin, galleries):
        for gallery in galleries:
            ActivityLog.objects.get_or_create(
                action=ActivityLog.Actions.CREATE,
                description=f"Created gallery '{gallery.title}'.",
                defaults={"actor": admin, "target_type": "Gallery", "target_id": str(gallery.pk)},
            )
        ActivityLog.objects.get_or_create(
            action=ActivityLog.Actions.SETTINGS,
            description="Seeded the demo dataset.",
            defaults={"actor": admin},
        )
        self.log("activity log entries")
