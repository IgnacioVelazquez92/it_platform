from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    # Más adelante:
    path("catalog/", include("apps.catalog.urls")),
]
