from __future__ import annotations

from graph_api.contracts.data_source import DataSourcePlugin
from graph_api.contracts.visualizer import VisualizerPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._data_sources: dict[str, DataSourcePlugin] = {}
        self._visualizers: dict[str, VisualizerPlugin] = {}

    def register_data_source(self, plugin: DataSourcePlugin) -> None:
        self._data_sources[plugin.plugin_id] = plugin

    def register_visualizer(self, plugin: VisualizerPlugin) -> None:
        self._visualizers[plugin.plugin_id] = plugin

    def get_data_source(self, plugin_id: str) -> DataSourcePlugin:
        return self._data_sources[plugin_id]

    def get_visualizer(self, plugin_id: str) -> VisualizerPlugin:
        return self._visualizers[plugin_id]

    def list_data_sources(self) -> list[DataSourcePlugin]:
        return list(self._data_sources.values())

    def list_visualizers(self) -> list[VisualizerPlugin]:
        return list(self._visualizers.values())
