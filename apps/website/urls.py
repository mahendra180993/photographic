from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("portfolio/", views.PortfolioListView.as_view(), name="portfolio"),
    path("portfolio/<slug:slug>/", views.PortfolioDetailView.as_view(), name="portfolio_detail"),
    path("services/", views.ServiceListView.as_view(), name="services"),
    path("services/<slug:slug>/", views.ServiceDetailView.as_view(), name="service_detail"),
    path("kind-words/", views.TestimonialListView.as_view(), name="testimonials"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("contact/thank-you/", views.ContactThanksView.as_view(), name="contact_thanks"),
]