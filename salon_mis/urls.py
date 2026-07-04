from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("masters/", include("masters.urls")),
    path("inventory/", include("inventory.urls")),
    path("reports/", include("reports.urls")),
]
