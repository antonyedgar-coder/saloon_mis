from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.SalonLoginView.as_view(), name="login"),
    path("logout/", views.SalonLogoutView.as_view(), name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("settings/", views.SettingsHubView.as_view(), name="settings"),
]
