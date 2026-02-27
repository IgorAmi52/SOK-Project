"""Web-framework integration layer placeholder.

Django and Flask adapters will live here in later phase.
"""

from __future__ import annotations

from graph_platform.core.plugin_registry import PluginRegistry


def create_plugin_registry() -> PluginRegistry:
    registry = PluginRegistry()

    try:
        from data_source_plugin_json import JsonDataSourcePlugin
    except ImportError:
        return registry

    registry.register_data_source(JsonDataSourcePlugin())
    return registry
