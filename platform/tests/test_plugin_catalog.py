from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for package_dir in ("api", "platform"):
    resolved = PROJECT_ROOT / package_dir
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))

from graph_api.contracts.data_source import DataSourcePlugin, PluginParameter
from graph_api.contracts.visualizer import VisualizerPlugin
from graph_api.model.graph import Graph
from graph_platform.app import (
    DATA_SOURCE_ENTRY_POINT_GROUP,
    VISUALIZER_ENTRY_POINT_GROUP,
    create_plugin_registry,
    describe_data_sources,
    describe_visualizers,
)
from graph_platform.core.plugin_registry import PluginRegistry


class DummyDataSourcePlugin(DataSourcePlugin):
    @property
    def plugin_id(self) -> str:
        return "dummy-data-source"

    @property
    def display_name(self) -> str:
        return "Dummy Data Source"

    @property
    def parameters(self) -> list[PluginParameter]:
        return [
            PluginParameter(
                name="file_path",
                description="Path to source file.",
                required=True,
            ),
            PluginParameter(
                name="mode",
                description="Parsing mode.",
                required=True,
                choices=("fast", "safe"),
            ),
            PluginParameter(
                name="graph_id",
                description="Optional graph identifier.",
                required=False,
            ),
        ]

    def load_graph(self, parameter_values: dict[str, str]) -> Graph:
        return Graph(graph_id=parameter_values.get("file_path", "dummy"))


class DummyVisualizerPlugin(VisualizerPlugin):
    @property
    def plugin_id(self) -> str:
        return "dummy-visualizer"

    @property
    def display_name(self) -> str:
        return "Dummy Visualizer"

    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        return "<div></div>"


class FakeEntryPoint:
    def __init__(self, loaded_object: object) -> None:
        self._loaded_object = loaded_object

    def load(self) -> object:
        return self._loaded_object


class FakeEntryPoints:
    def __init__(self, mapping: dict[str, list[FakeEntryPoint]]) -> None:
        self._mapping = mapping

    def select(self, *, group: str) -> list[FakeEntryPoint]:
        return self._mapping.get(group, [])


class PluginCatalogTests(unittest.TestCase):
    def test_create_plugin_registry_loads_entry_point_plugins(self) -> None:
        fake_entry_points = FakeEntryPoints(
            {
                DATA_SOURCE_ENTRY_POINT_GROUP: [FakeEntryPoint(DummyDataSourcePlugin)],
                VISUALIZER_ENTRY_POINT_GROUP: [FakeEntryPoint(DummyVisualizerPlugin)],
            }
        )

        with patch("graph_platform.app.metadata.entry_points", return_value=fake_entry_points):
            registry = create_plugin_registry()

        data_source_ids = {plugin.plugin_id for plugin in registry.list_data_sources()}
        visualizer_ids = {plugin.plugin_id for plugin in registry.list_visualizers()}

        self.assertIn("dummy-data-source", data_source_ids)
        self.assertIn("dummy-visualizer", visualizer_ids)

    def test_describe_data_sources_includes_parameter_metadata(self) -> None:
        registry = PluginRegistry()
        registry.register_data_source(DummyDataSourcePlugin())

        descriptors = describe_data_sources(registry)

        self.assertEqual(len(descriptors), 1)
        self.assertEqual(descriptors[0]["id"], "dummy-data-source")
        self.assertTrue(descriptors[0]["has_optional_parameters"])
        self.assertEqual(
            descriptors[0]["required_parameters"],
            [
                {
                    "name": "file_path",
                    "label": "File Path",
                    "description": "Path to source file.",
                    "required": True,
                    "choices": [],
                    "is_file_path": True,
                },
                {
                    "name": "mode",
                    "label": "Mode",
                    "description": "Parsing mode.",
                    "required": True,
                    "choices": ["fast", "safe"],
                    "is_file_path": False,
                },
            ],
        )
        self.assertEqual(
            descriptors[0]["optional_parameters"],
            [
                {
                    "name": "graph_id",
                    "label": "Graph Id",
                    "description": "Optional graph identifier.",
                    "required": False,
                    "choices": [],
                    "is_file_path": False,
                },
            ],
        )
        self.assertEqual(
            descriptors[0]["parameters"],
            [
                {
                    "name": "file_path",
                    "label": "File Path",
                    "description": "Path to source file.",
                    "required": True,
                    "choices": [],
                    "is_file_path": True,
                },
                {
                    "name": "mode",
                    "label": "Mode",
                    "description": "Parsing mode.",
                    "required": True,
                    "choices": ["fast", "safe"],
                    "is_file_path": False,
                },
                {
                    "name": "graph_id",
                    "label": "Graph Id",
                    "description": "Optional graph identifier.",
                    "required": False,
                    "choices": [],
                    "is_file_path": False,
                },
            ],
        )

    def test_describe_visualizers_returns_id_and_name(self) -> None:
        registry = PluginRegistry()
        registry.register_visualizer(DummyVisualizerPlugin())

        self.assertEqual(
            describe_visualizers(registry),
            [{"id": "dummy-visualizer", "name": "Dummy Visualizer"}],
        )


if __name__ == "__main__":
    unittest.main()
