# Lumina Atelier

A production-ready **photography studio website + client gallery management platform**, built with
Django 5, a custom studio dashboard (no `django.contrib.admin` UI), and a cinematic front end using
Tailwind, GSAP, Lenis, Swiper, LightGallery and Three.js.

---

## What is inside

| Area | What it does |
| --- | --- |
| **Public website** | Home, About, Portfolio (collections + detail), Services (list + detail), Testimonials, Contact with enquiry form, robots.txt, sitemap.xml |
| **Client area** (`/client/`) | Login, gallery list, gallery viewer with lightbox, photo selection, album submission, single + ZIP downloads, share-link galleries with access codes, expiry handling, notifications |
| **Studio dashboard** (`/studio/`) | Overview with live metrics and charts, customers, photographers, galleries with bulk upload and drag-reorder, album requests, enquiries inbox, portfolio CMS, services, team, FAQs, testimonials, SEO + website settings, analytics, activity log, studio logins |
| **Platform** | Custom user model with roles, email-or-username auth backend, signals-driven notifications and emails, audit logging, maintenance mode, S3-ready storage, Docker |

### Brand

Ink `#050505`, ivory `#F3EFE6`, gold `#D4AF37`, Clash Display + General Sans (Fontshare CDN).

---

## Quick start (local, SQLite)

```bash
# 1. Virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Dependencies
pip install -r requirements.txt

# 3. Configuration (optional - sensible defaults are built in)
cp .env.example .env

# 4. Database + demo content
python manage.py migrate
python manage.py seed_demo

# 5. Run
python manage.py runserver
```

Open <http://localhost:8000>.

### Demo logins created by `seed_demo`

| Role | Username | Password | Lands on |
| --- | --- | --- | --- |
| Studio admin | `admin` | `admin123` | `/studio/` |
| Photographer | `elise` | `studio123` | `/studio/` |
| Client | `client` | `client123` | `/client/` |
| Client (share-link demo) | `marchetti` | `client123` | `/client/` |

Clients may sign in with **either** their username or their email address.

`seed_demo` downloads real photographs from the Unsplash CDN, so every gallery, collection and
service page is populated with authentic imagery. An internet connection is required unless you
pass `--no-images`; a download that fails quietly falls back to a Pillow placeholder rather than
aborting the seed. Useful flags:

```bash
python manage.py seed_demo --reset            # wipe demo content and rebuild
python manage.py seed_demo --refresh-images   # keep the data, re-download every photograph
python manage.py seed_demo --no-images        # fast, text-only seed (works offline)
```

---

## Project layout

```
config/                 settings, root urlconf, wsgi/asgi
apps/
  common/               abstract models, mixins, upload paths, template tags
  core/                 context processors, middleware, sitemaps, robots, seed command
  accounts/             custom User, managers, auth backend, login/reset views
  customers/            Customer, Photographer
  galleries/            Gallery, GalleryImage, GalleryCategory, DownloadHistory,
                        GalleryAccessLog + the whole client-facing gallery flow
  albums/               AlbumRequest, AlbumSelection
  notifications/        Notification + email/in-app fan-out services
  cms/                  WebsiteSettings, SEOSettings, TeamMember, FAQ, Testimonial, ContactMessage
  portfolio/            PortfolioCategory, PortfolioImage
  services/             Service
  analytics/            ActivityLog
  website/              public marketing views
  dashboard/            the custom studio admin (CBV CRUD over every model)
templates/              base + partials, website/, accounts/, client/, dashboard/, errors/
static/css|js|img/      main.css, main.js, animations.js, gallery.js, dashboard.js, three-hero.js
```

All views are **class-based**. CRUD in the dashboard is built on reusable
`DashboardListView` / `DashboardCreateView` / `DashboardUpdateView` / `DashboardDeleteView`
bases plus three generic templates, so adding a managed model is a handful of lines.

---

## Key flows

### Delivering a gallery

1. `/studio/customers/new/` - create the client (tick **Create a client login** to issue credentials).
2. `/studio/galleries/new/` - create the gallery, pick the customer, set downloads / selection limit /
   watermark / expiry / visibility.
3. On the gallery page, drag photographs onto the dropzone and upload in bulk.
4. Set the status to **Ready** or **Delivered** - a signal emails the client and creates an in-app
   notification. **Notify client** re-sends it on demand.

### Visibility modes

| Mode | Who can open it |
| --- | --- |
| `private` | Only the linked client login (studio staff always have access) |
| `code` | Anyone with the share URL **and** the access code (stored in the session once unlocked) |
| `public` | Anyone with the link |

Expired galleries return HTTP 410 with a friendly "request access" page.

### Selection and downloads

Clients toggle photographs with a JSON endpoint (`/client/gallery/<slug>/select/`), respecting
`selection_limit`, then submit - which creates/updates an `AlbumRequest`, flips it to *submitted*
and notifies both sides. Every download goes through a permission-checked view that writes a
`DownloadHistory` row and a `GalleryAccessLog` entry; bulk download streams a ZIP built on the fly.

---

## Configuration

Everything is environment-driven (see `.env.example`). Highlights:

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | Set `False` in production |
| `DJANGO_SECRET_KEY` | dev key | **Must** be changed for production |
| `DATABASE_URL` | empty | Empty = SQLite. Set `postgres://user:pass@host:5432/db` for Postgres |
| `EMAIL_BACKEND` | console | Emails print to the console in development |
| `USE_S3` | `False` | `True` switches media to `django-storages` S3 (install `boto3`) |
| `GALLERY_DEFAULT_EXPIRY_DAYS` | `90` | Default gallery lifetime |
| `GALLERY_ZIP_MAX_IMAGES` | `300` | Safety cap on bulk ZIP downloads |
| `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | `False` | Turn on behind HTTPS |

### PostgreSQL

```bash
DATABASE_URL=postgres://lumina:lumina@localhost:5432/lumina
python manage.py migrate
```

---

## Docker

```bash
docker compose up --build
docker compose exec web python manage.py seed_demo
```

Serves on <http://localhost:8000> with Postgres 16, Gunicorn, WhiteNoise for static files, and
named volumes for media and static. The container runs migrations and `collectstatic` on start and
exposes a health check at `/health/`.

---

## Netlify

Netlify does **not** run Python/Django as a serverless function (only JavaScript, TypeScript, and
Go). This project includes a **Netlify front-end** setup that:

1. Builds and publishes collected static files (`/static/`) from the global CDN.
2. Proxies all other routes through `netlify/functions/django.mts` to a Django backend you host
   elsewhere (Render, Railway, Fly.io, or your own Docker server).

### Deploy in two steps

**Step 1 — Django backend** (pick one):

```bash
# Local / VPS: use Docker Compose (see above), or connect the repo on Render.com
# (render.yaml is included — it provisions Postgres + the web service automatically).
```

On the backend, set:

| Variable | Example |
| --- | --- |
| `DJANGO_ALLOWED_HOSTS` | `your-app.onrender.com,.netlify.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-site.netlify.app,https://your-app.onrender.com` |
| `SITE_DOMAIN` | `https://your-site.netlify.app` |
| `DATABASE_URL` | Postgres connection string (required in production) |
| `USE_S3` | `True` for gallery uploads (Netlify has no persistent disk) |

Then run migrations and seed on the backend:

```bash
python manage.py migrate
python manage.py seed_demo   # optional demo content
```

**Step 2 — Netlify site**

1. Connect this repository on [Netlify](https://app.netlify.com/).
2. Netlify reads `netlify.toml` automatically (`scripts/netlify_build.sh` runs
   `collectstatic`).
3. In **Site settings → Environment variables**, add:

| Variable | Scope | Value |
| --- | --- | --- |
| `DJANGO_BACKEND_URL` | **Functions** | `https://your-app.onrender.com` (no trailing slash) |
| `DJANGO_SECRET_KEY` | Build | same value as the backend |
| `SITE_DOMAIN` | Build | `https://your-site.netlify.app` |

4. Deploy. Static assets are served from Netlify; pages, logins, and uploads go through the proxy
   to your Django server.

### Local Netlify preview

```bash
npm install
pip install -r requirements.txt
export DJANGO_BACKEND_URL=http://localhost:8000
netlify dev
```

### Limitations on Netlify

- **No local media storage** — enable `USE_S3` (or another object store) for gallery uploads.
- **Function timeout** — large ZIP downloads or bulk uploads may hit Netlify’s function limits;
  the backend still processes them, but the proxy may time out on very slow responses.
- **Cold starts** — first request after idle may be slower on the free Render tier.
- For a single-platform deploy with no proxy, use **Docker Compose** locally or **Render/Railway**
  with the included `Dockerfile` instead of Netlify.

---

## Useful commands

```bash
python manage.py check                 # system checks
python manage.py makemigrations        # after model changes
python manage.py migrate
python manage.py seed_demo --reset     # rebuild demo content
python manage.py createsuperuser       # a real studio admin
python manage.py collectstatic         # production static build
```

---

## Security notes

- Custom `User` model with a `role` field; access is enforced by `StaffRequiredMixin`,
  `AdminRequiredMixin` and `ClientRequiredMixin` rather than Django's staff flag alone.
- `EmailOrUsernameModelBackend` runs a dummy password hash for unknown users to equalise timing.
- Failed sign-ins are recorded in `ActivityLog`; every gallery view, unlock, selection, submission
  and download is recorded in `GalleryAccessLog`.
- Session cookies are HttpOnly and SameSite=Lax; HSTS, SSL redirect and secure cookies switch on
  via environment variables when `DEBUG=False`.
- The contact form carries a honeypot field and stores the submitter IP.

---

## Known limitations

- **Media protection in development.** Gallery originals live under `MEDIA_ROOT/galleries/` and, with
  `DEBUG=True`, Django serves that path directly so thumbnails render. Downloads always go through the
  permission-checked, audited view, but in production you should block `/media/galleries/` at the web
  server (or use the S3 backend, which issues signed URLs) and let `ImageDownloadView` serve originals
  via `X-Accel-Redirect` / `X-Sendfile`.
- **Watermarking is a display-time overlay** (a CSS layer over the preview) driven by
  `watermark_enabled` / `watermark_text`. Originals are not burned in; add a Pillow post-processing
  step if you need baked watermarks.
- **Bulk ZIP downloads are built in memory** and capped by `GALLERY_ZIP_MAX_IMAGES`. For very large
  galleries, move this to a background job (Celery/RQ) writing to object storage.
- **No thumbnail pipeline.** Full-size images are served to the browser with `loading="lazy"`.
  Adding `django-imagekit` or `sorl-thumbnail` is the natural next step for large galleries.
- **Emails are stubs in development** - the console backend prints them. Configure SMTP (or an API
  backend) for real delivery. Password reset works end to end once SMTP is set.
- **Tailwind runs from the CDN** for development speed. For production, install the Tailwind CLI and
  build a purged stylesheet to remove the CDN runtime.
- **Uploads are synchronous.** Bulk uploads of a few hundred large files will hold the request open;
  the front end shows a progress state, but a background worker is advisable at scale.
- **No automated test suite yet** - the flows were verified with an end-to-end smoke pass across all
  70 public, client and dashboard routes.

---

## License

Proprietary demo project. Replace this section with your own license before shipping.