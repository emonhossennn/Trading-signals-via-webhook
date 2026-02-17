"""
URL configuration for the trading signal service.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("signals_app.urls")),
]
