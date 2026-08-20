from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.ClientLoginView.as_view(), name="client_login"),
    path("studio-login/", views.StudioLoginView.as_view(), name="admin_login"),
    path("logout/", views.StudioLogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password/reset/sent/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password/reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password/reset/done/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]