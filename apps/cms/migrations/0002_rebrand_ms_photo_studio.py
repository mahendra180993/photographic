from django.db import migrations


def rebrand(apps, schema_editor):
    WebsiteSettings = apps.get_model("cms", "WebsiteSettings")
    SEOSettings = apps.get_model("cms", "SEOSettings")

    for site in WebsiteSettings.objects.all():
        site.site_name = "MS Photo Studio"
        if site.about_body:
            site.about_body = site.about_body.replace("Lumina Atelier", "MS Photo Studio")
        if site.email and "luminaatelier" in site.email:
            site.email = "studio@msphotostudio.com"
        if site.booking_email and "luminaatelier" in site.booking_email:
            site.booking_email = "bookings@msphotostudio.com"
        site.save()

    for seo in SEOSettings.objects.all():
        if seo.meta_title:
            seo.meta_title = seo.meta_title.replace("Lumina Atelier", "MS Photo Studio")
        else:
            seo.meta_title = "MS Photo Studio | Fine Art Photography Studio"
        if seo.meta_description:
            seo.meta_description = seo.meta_description.replace("Lumina Atelier", "MS Photo Studio")
        seo.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(rebrand, noop),
    ]
