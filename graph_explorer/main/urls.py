from django.urls import path

from .views import api_workspace, api_workspace_detail, home, workspace

urlpatterns = [
    path("", home, name="home"),
    path("workspace/", workspace, name="workspace"),
    path("api/workspace/", api_workspace, name="api_workspace"),
    path("api/workspace/<str:workspace_id>/", api_workspace_detail, name="api_workspace_detail"),
]
