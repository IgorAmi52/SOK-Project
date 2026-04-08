from __future__ import annotations

from graph_api.contracts.data_source import DataSourcePlugin
from graph_api.contracts.visualizer import VisualizerPlugin


# Pattern: Registry — central catalog for discovering and retrieving plugin instances at runtime
class PluginRegistry:
    """Central registry for data-source and visualizer plugins."""

    def __init__(self) -> None:
        self._data_sources: dict[str, DataSourcePlugin] = {}
        self._visualizers: dict[str, VisualizerPlugin] = {}

    def register_data_source(self, plugin: DataSourcePlugin) -> None:
        """Register a data-source plugin.

        Args:
            plugin: The data-source plugin instance to register.
        """
        self._data_sources[plugin.plugin_id] = plugin

    def register_visualizer(self, plugin: VisualizerPlugin) -> None:
        """Register a visualizer plugin.

        Args:
            plugin: The visualizer plugin instance to register.
        """
        self._visualizers[plugin.plugin_id] = plugin

    def get_data_source(self, plugin_id: str) -> DataSourcePlugin:
        """Retrieve a registered data-source plugin by its identifier.

        Args:
            plugin_id: Unique identifier of the data-source plugin.

        Returns:
            The matching DataSourcePlugin instance.
        """
        return self._data_sources[plugin_id]

    def get_visualizer(self, plugin_id: str) -> VisualizerPlugin:
        """Retrieve a registered visualizer plugin by its identifier.

        Args:
            plugin_id: Unique identifier of the visualizer plugin.

        Returns:
            The matching VisualizerPlugin instance.
        """
        return self._visualizers[plugin_id]

    def list_data_sources(self) -> list[DataSourcePlugin]:
        """Return all registered data-source plugins."""
        return list(self._data_sources.values())

    def list_visualizers(self) -> list[VisualizerPlugin]:
        """Return all registered visualizer plugins."""
        return list(self._visualizers.values())
