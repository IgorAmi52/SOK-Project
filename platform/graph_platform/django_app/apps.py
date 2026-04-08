from django.apps import AppConfig


class GraphPlatformDjangoConfig(AppConfig):
    """Django application configuration for the graph platform."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "graph_platform.django_app"
    label = "graph_platform_django"
