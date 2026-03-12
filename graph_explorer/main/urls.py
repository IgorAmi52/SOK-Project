from django.urls import path

from .views import api_cli, home, workspace

urlpatterns = [
    path("", home, name="home"),
    path("workspace/", workspace, name="workspace"),
    path("api/cli/", api_cli, name="api_cli"),
]
