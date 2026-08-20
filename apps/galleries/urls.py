from django.urls import path

from . import views

app_name = "client"

urlpatterns = [
    path("", views.ClientIndexView.as_view(), name="index"),
    path("notifications/", views.ClientNotificationsView.as_view(), name="notifications"),
    path("help/", views.ClientHelpView.as_view(), name="help"),
    path("share/<uuid:token>/", views.GalleryShareView.as_view(), name="gallery_share"),
    path("gallery/<slug:slug>/", views.GalleryDetailView.as_view(), name="gallery_detail"),
    path("gallery/<slug:slug>/select/", views.ToggleSelectionView.as_view(), name="toggle_selection"),
    path("gallery/<slug:slug>/submit/", views.SubmitSelectionView.as_view(), name="submit_selection"),
    path("gallery/<slug:slug>/download-all/", views.GalleryDownloadAllView.as_view(), name="download_all"),
    path(
        "gallery/<slug:slug>/download/<uuid:image_uuid>/",
        views.ImageDownloadView.as_view(),
        name="image_download",
    ),
]