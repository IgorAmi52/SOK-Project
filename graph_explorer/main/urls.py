from django.urls import path

from .views import home, workspace

urlpatterns = [
    path("", home, name="home"),
    path("workspace/", workspace, name="workspace"),
]
