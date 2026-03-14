from __future__ import annotations

from importlib import metadata
from typing import Callable, TypeVar, cast

from graph_api.contracts.data_source import DataSourcePlugin, PluginParameter
from graph_api.contracts.visualizer import VisualizerPlugin
from graph_platform.core.plugin_registry import PluginRegistry

DATA_SOURCE_ENTRY_POINT_GROUP = "graph_platform.data_source_plugins"
VISUALIZER_ENTRY_POINT_GROUP = "graph_platform.visualizer_plugins"


def create_plugin_registry() -> PluginRegistry:
    registry = PluginRegistry()
    _register_entry_point_data_sources(registry)
    _register_entry_point_visualizers(registry)
    _register_builtin_data_sources(registry)
    _register_builtin_visualizers(registry)
    return registry


def describe_data_sources(registry: PluginRegistry) -> list[dict[str, object]]:
    return [
        {
            "id": plugin.plugin_id,
            "name": plugin.display_name,
            "parameters": serialized_parameters,
            "required_parameters": [
                parameter
                for parameter in serialized_parameters
                if parameter["required"]
            ],
            "optional_parameters": [
                parameter
                for parameter in serialized_parameters
                if not parameter["required"]
            ],
            "has_optional_parameters": any(
                not parameter["required"] for parameter in serialized_parameters
            ),
        }
        for plugin in sorted(
            registry.list_data_sources(),
            key=lambda plugin: (plugin.display_name.lower(), plugin.plugin_id),
        )
        for serialized_parameters in [[
                _serialize_plugin_parameter(parameter)
                for parameter in plugin.parameters
            ]]
    ]


def describe_visualizers(registry: PluginRegistry) -> list[dict[str, str]]:
    return [
        {"id": plugin.plugin_id, "name": plugin.display_name}
        for plugin in sorted(
            registry.list_visualizers(),
            key=lambda plugin: (plugin.display_name.lower(), plugin.plugin_id),
        )
    ]


def _serialize_plugin_parameter(parameter: PluginParameter) -> dict[str, object]:
    return {
        "name": parameter.name,
        "label": parameter.name.replace("_", " ").title(),
        "description": parameter.description,
        "required": parameter.required,
        "choices": list(parameter.choices),
        "is_file_path": parameter.name == "file_path",
    }


def _register_entry_point_data_sources(registry: PluginRegistry) -> None:
    _register_entry_point_plugins(
        registry=registry,
        group=DATA_SOURCE_ENTRY_POINT_GROUP,
        register=registry.register_data_source,
    )


def _register_entry_point_visualizers(registry: PluginRegistry) -> None:
    _register_entry_point_plugins(
        registry=registry,
        group=VISUALIZER_ENTRY_POINT_GROUP,
        register=registry.register_visualizer,
    )


PluginT = TypeVar("PluginT")


def _register_entry_point_plugins(
    registry: PluginRegistry,
    group: str,
    register: Callable[[PluginT], None],
) -> None:
    for entry_point in _select_entry_points(group):
        try:
            loaded = entry_point.load()
            plugin = loaded() if callable(loaded) else loaded
            register(cast(PluginT, plugin))
        except Exception:
            continue


def _select_entry_points(group: str) -> list[metadata.EntryPoint]:
    discovered = metadata.entry_points()
    if hasattr(discovered, "select"):
        return list(discovered.select(group=group))
    return [ep for ep in discovered if getattr(ep, "group", None) == group]


def _register_builtin_data_sources(registry: PluginRegistry) -> None:
    _register_builtin_plugin(
        registry=registry,
        plugin_id="json-data-source",
        register=registry.register_data_source,
        factory=_load_json_data_source,
    )
    _register_builtin_plugin(
        registry=registry,
        plugin_id="csv_data_source",
        register=registry.register_data_source,
        factory=_load_csv_data_source,
    )
    _register_builtin_plugin(
        registry=registry,
        plugin_id="yaml-data-source",
        register=registry.register_data_source,
        factory=_load_yaml_data_source,
    )


def _register_builtin_visualizers(registry: PluginRegistry) -> None:
    _register_builtin_plugin(
        registry=registry,
        plugin_id="simple-visualizer",
        register=registry.register_visualizer,
        factory=_load_simple_visualizer,
    )
    _register_builtin_plugin(
        registry=registry,
        plugin_id="block-visualizer",
        register=registry.register_visualizer,
        factory=_load_block_visualizer,
    )


def _register_builtin_plugin(
    registry: PluginRegistry,
    plugin_id: str,
    register: Callable[[PluginT], None],
    factory: Callable[[], PluginT],
) -> None:
    if _registry_contains_plugin(registry, plugin_id):
        return

    try:
        register(factory())
    except ImportError:
        pass


def _registry_contains_plugin(registry: PluginRegistry, plugin_id: str) -> bool:
    return any(plugin.plugin_id == plugin_id for plugin in registry.list_data_sources()) or any(
        plugin.plugin_id == plugin_id for plugin in registry.list_visualizers()
    )


def _load_json_data_source() -> DataSourcePlugin:
    from data_source_plugin_json import JsonDataSourcePlugin

    return JsonDataSourcePlugin()


def _load_csv_data_source() -> DataSourcePlugin:
    from csv_data_source.plugin import CsvDataSourcePlugin

    return CsvDataSourcePlugin()


def _load_yaml_data_source() -> DataSourcePlugin:
    from yaml_data_source.plugin import YamlDataSourcePlugin

    return YamlDataSourcePlugin()


def _load_simple_visualizer() -> VisualizerPlugin:
    from simple_visualizer import SimpleVisualizerPlugin

    return SimpleVisualizerPlugin()


def _load_block_visualizer() -> VisualizerPlugin:
    from block_visualizer import BlockVisualizerPlugin

    return BlockVisualizerPlugin()
