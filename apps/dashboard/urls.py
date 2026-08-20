from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardIndexView.as_view(), name="index"),

    # Customers -----------------------------------------------------------
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/new/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("customers/<int:pk>/", views.CustomerDetailView.as_view(), name="customer_detail"),
    path("customers/<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer_update"),
    path("customers/<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="customer_delete"),

    # Photographers -------------------------------------------------------
    path("photographers/", views.PhotographerListView.as_view(), name="photographer_list"),
    path("photographers/new/", views.PhotographerCreateView.as_view(), name="photographer_create"),
    path("photographers/<int:pk>/edit/", views.PhotographerUpdateView.as_view(), name="photographer_update"),
    path("photographers/<int:pk>/delete/", views.PhotographerDeleteView.as_view(), name="photographer_delete"),

    # Galleries -----------------------------------------------------------
    path("galleries/", views.GalleryListView.as_view(), name="gallery_list"),
    path("galleries/new/", views.GalleryCreateView.as_view(), name="gallery_create"),
    path("galleries/<int:pk>/", views.GalleryDetailView.as_view(), name="gallery_detail"),
    path("galleries/<int:pk>/edit/", views.GalleryUpdateView.as_view(), name="gallery_update"),
    path("galleries/<int:pk>/delete/", views.GalleryDeleteView.as_view(), name="gallery_delete"),
    path("galleries/<int:pk>/upload/", views.GalleryUploadView.as_view(), name="gallery_upload"),
    path("galleries/<int:pk>/rotate-code/", views.GalleryRotateCodeView.as_view(), name="gallery_rotate_code"),
    path("galleries/<int:pk>/notify/", views.GalleryNotifyView.as_view(), name="gallery_notify"),
    path("gallery-images/<int:pk>/delete/", views.GalleryImageDeleteView.as_view(), name="gallery_image_delete"),
    path("gallery-images/<int:pk>/cover/", views.GalleryImageCoverView.as_view(), name="gallery_image_cover"),
    path("gallery-images/<int:pk>/toggle/", views.GalleryImageToggleView.as_view(), name="gallery_image_toggle"),
    path("gallery-images/reorder/", views.GalleryImageReorderView.as_view(), name="gallery_image_reorder"),
    path("gallery-categories/", views.GalleryCategoryListView.as_view(), name="gallery_category_list"),
    path("gallery-categories/new/", views.GalleryCategoryCreateView.as_view(), name="gallery_category_create"),
    path("gallery-categories/<int:pk>/edit/", views.GalleryCategoryUpdateView.as_view(),
         name="gallery_category_update"),
    path("gallery-categories/<int:pk>/delete/", views.GalleryCategoryDeleteView.as_view(),
         name="gallery_category_delete"),

    # Albums & selections -------------------------------------------------
    path("albums/", views.AlbumRequestListView.as_view(), name="album_list"),
    path("albums/<int:pk>/", views.AlbumRequestDetailView.as_view(), name="album_detail"),

    # Enquiries -----------------------------------------------------------
    path("messages/", views.ContactMessageListView.as_view(), name="message_list"),
    path("messages/<int:pk>/", views.ContactMessageDetailView.as_view(), name="message_detail"),

    # Portfolio -----------------------------------------------------------
    path("portfolio/", views.PortfolioCategoryListView.as_view(), name="portfolio_category_list"),
    path("portfolio/new/", views.PortfolioCategoryCreateView.as_view(), name="portfolio_category_create"),
    path("portfolio/<int:pk>/edit/", views.PortfolioCategoryUpdateView.as_view(),
         name="portfolio_category_update"),
    path("portfolio/<int:pk>/delete/", views.PortfolioCategoryDeleteView.as_view(),
         name="portfolio_category_delete"),
    path("portfolio/photographs/", views.PortfolioImageListView.as_view(), name="portfolio_image_list"),
    path("portfolio/photographs/new/", views.PortfolioImageCreateView.as_view(), name="portfolio_image_create"),
    path("portfolio/photographs/upload/", views.PortfolioBulkUploadView.as_view(), name="portfolio_bulk_upload"),
    path("portfolio/photographs/<int:pk>/edit/", views.PortfolioImageUpdateView.as_view(),
         name="portfolio_image_update"),
    path("portfolio/photographs/<int:pk>/delete/", views.PortfolioImageDeleteView.as_view(),
         name="portfolio_image_delete"),

    # Services ------------------------------------------------------------
    path("services/", views.ServiceListView.as_view(), name="service_list"),
    path("services/new/", views.ServiceCreateView.as_view(), name="service_create"),
    path("services/<int:pk>/edit/", views.ServiceUpdateView.as_view(), name="service_update"),
    path("services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),

    # Team ----------------------------------------------------------------
    path("team/", views.TeamMemberListView.as_view(), name="team_list"),
    path("team/new/", views.TeamMemberCreateView.as_view(), name="team_create"),
    path("team/<int:pk>/edit/", views.TeamMemberUpdateView.as_view(), name="team_update"),
    path("team/<int:pk>/delete/", views.TeamMemberDeleteView.as_view(), name="team_delete"),

    # FAQs ----------------------------------------------------------------
    path("faqs/", views.FAQListView.as_view(), name="faq_list"),
    path("faqs/new/", views.FAQCreateView.as_view(), name="faq_create"),
    path("faqs/<int:pk>/edit/", views.FAQUpdateView.as_view(), name="faq_update"),
    path("faqs/<int:pk>/delete/", views.FAQDeleteView.as_view(), name="faq_delete"),

    # Testimonials --------------------------------------------------------
    path("testimonials/", views.TestimonialListView.as_view(), name="testimonial_list"),
    path("testimonials/new/", views.TestimonialCreateView.as_view(), name="testimonial_create"),
    path("testimonials/<int:pk>/edit/", views.TestimonialUpdateView.as_view(), name="testimonial_update"),
    path("testimonials/<int:pk>/delete/", views.TestimonialDeleteView.as_view(), name="testimonial_delete"),

    # Settings / team logins ----------------------------------------------
    path("settings/", views.WebsiteSettingsView.as_view(), name="settings_site"),
    path("settings/seo/", views.SEOSettingsView.as_view(), name="settings_seo"),
    path("settings/logins/", views.StaffUserListView.as_view(), name="staff_list"),
    path("settings/logins/new/", views.StaffUserCreateView.as_view(), name="staff_create"),
    path("settings/logins/<int:pk>/edit/", views.StaffUserUpdateView.as_view(), name="staff_update"),

    # Insights ------------------------------------------------------------
    path("analytics/", views.AnalyticsView.as_view(), name="analytics"),
    path("activity/", views.ActivityLogView.as_view(), name="activity"),
    path("notifications/", views.NotificationListView.as_view(), name="notifications"),
]