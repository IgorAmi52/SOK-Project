"""Root URL configuration for the Graph Explorer Django project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('graph_platform.django_app.urls')),
]
