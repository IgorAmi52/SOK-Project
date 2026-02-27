from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for package_dir in ("api", "platform", "data_source_csv"):
    resolved = PROJECT_ROOT / package_dir
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))

from csv_data_source.errors import CsvParameterError, CsvParsingError
from csv_data_source.models import CsvLoadConfig, CsvRows, ParsedEdge, ParsedGraphData
from csv_data_source.pipeline import CsvParsingPipeline
from csv_data_source.plugin import CsvDataSourcePlugin
from graph_api.model.edge import Edge
from graph_api.model.graph import Graph
from graph_api.model.node import Node
from graph_platform.core.plugin_registry import PluginRegistry

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class TemplateMethodPipelineTests(unittest.TestCase):
    class SpyPipeline(CsvParsingPipeline):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def load(self, parameter_values: dict[str, str]) -> CsvLoadConfig:
            self.calls.append("load")
            return CsvLoadConfig(
                file_path=Path("fake.csv"),
                format_name="edge_list",
                delimiter=",",
                graph_id="spy",
            )

        def read(self, config: CsvLoadConfig) -> CsvRows:
            self.calls.append("read")
            return CsvRows(fieldnames=("source", "target"), rows=[{"source": "A", "target": "B"}])

        def parse(self, csv_rows: CsvRows, config: CsvLoadConfig) -> ParsedGraphData:
            self.calls.append("parse")
            return ParsedGraphData(
                node_attributes={"A": {}, "B": {}},
                edges=[
                    ParsedEdge(
                        edge_id="e1",
                        source_id="A",
                        target_id="B",
                        directed=True,
                        attributes={},
                    )
                ],
            )

        def build(self, parsed_graph: ParsedGraphData, config: CsvLoadConfig) -> Graph:
            self.calls.append("build")
            graph = Graph(graph_id=config.graph_id, directed_default=True, allow_cycles=True)
            graph.add_node(Node(node_id="A"))
            graph.add_node(Node(node_id="B"))
            graph.add_edge(Edge(edge_id="e1", source_id="A", target_id="B", directed=True))
            return graph

        def validate(self, graph: Graph, config: CsvLoadConfig) -> None:
            self.calls.append("validate")

    def test_template_method_executes_steps_in_order(self) -> None:
        pipeline = self.SpyPipeline()
        graph = pipeline.execute({})
        self.assertEqual(graph.graph_id, "spy")
        self.assertEqual(pipeline.calls, ["load", "read", "parse", "build", "validate"])


class CsvDataSourcePluginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = CsvDataSourcePlugin()

    def _params(self, fixture_name: str, csv_format: str = "edge_list", **overrides: str) -> dict[str, str]:
        params = {
            "file_path": str(FIXTURES_DIR / fixture_name),
            "format": csv_format,
        }
        params.update(overrides)
        return params

    def test_parameters_metadata_is_exposed(self) -> None:
        parameter_names = {parameter.name for parameter in self.plugin.parameters}
        self.assertEqual(parameter_names, {"file_path", "format", "delimiter", "graph_id"})

    def test_edge_list_happy_path_builds_graph_with_inferred_types(self) -> None:
        graph = self.plugin.load_graph(self._params("edge_list_valid.csv"))

        self.assertEqual(graph.graph_id, "edge_list_valid")
        self.assertEqual(set(graph.nodes.keys()), {"n1", "n2", "n3"})
        self.assertEqual(set(graph.edges.keys()), {"e1", "e2"})

        self.assertIsInstance(graph.nodes["n1"].attributes["age"], int)
        self.assertEqual(graph.nodes["n1"].attributes["age"], 21)
        self.assertIsInstance(graph.nodes["n1"].attributes["joined"], date)
        self.assertIsInstance(graph.edges["e1"].attributes["weight"], float)
        self.assertFalse(graph.edges["e2"].directed)

    def test_missing_required_parameter_raises_error(self) -> None:
        with self.assertRaises(CsvParameterError):
            self.plugin.load_graph({"format": "edge_list"})

    def test_unsupported_format_raises_error(self) -> None:
        with self.assertRaises(CsvParameterError):
            self.plugin.load_graph(
                {
                    "file_path": str(FIXTURES_DIR / "edge_list_valid.csv"),
                    "format": "unknown_format",
                }
            )

    def test_missing_required_columns_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(self._params("edge_list_missing_columns.csv"))

    def test_invalid_directed_value_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(self._params("edge_list_invalid_directed.csv"))

    def test_adjacency_list_happy_path_builds_graph(self) -> None:
        graph = self.plugin.load_graph(
            self._params("adjacency_list_valid.csv", csv_format="adjacency_list")
        )

        self.assertEqual(graph.graph_id, "adjacency_list_valid")
        self.assertEqual(set(graph.nodes.keys()), {"n1", "n2", "n3", "n4"})
        self.assertEqual(len(graph.edges), 4)
        self.assertTrue(graph.edges["e1"].directed)
        self.assertFalse(graph.edges["e4"].directed)
        self.assertEqual(graph.nodes["n1"].attributes["role"], "admin")
        self.assertEqual(graph.edges["e1"].attributes["weight"], 0.5)
        self.assertIsInstance(graph.nodes["n1"].attributes["joined"], date)

    def test_adjacency_list_cycle_input_is_supported(self) -> None:
        graph = self.plugin.load_graph(
            self._params("adjacency_list_cycle.csv", csv_format="adjacency_list")
        )
        pairs = {(edge.source_id, edge.target_id) for edge in graph.edges.values()}
        self.assertEqual(pairs, {("n1", "n2"), ("n2", "n1")})

    def test_adjacency_list_missing_required_columns_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(
                self._params(
                    "adjacency_list_missing_columns.csv",
                    csv_format="adjacency_list",
                )
            )

    def test_adjacency_list_invalid_directed_value_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(
                self._params(
                    "adjacency_list_invalid_directed.csv",
                    csv_format="adjacency_list",
                )
            )

    def test_adjacency_list_single_edge_id_with_multiple_targets_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(
                self._params(
                    "adjacency_list_invalid_edge_id.csv",
                    csv_format="adjacency_list",
                )
            )

    def test_matrix_happy_path_builds_graph(self) -> None:
        graph = self.plugin.load_graph(self._params("matrix_valid.csv", csv_format="matrix"))

        self.assertEqual(graph.graph_id, "matrix_valid")
        self.assertEqual(set(graph.nodes.keys()), {"n1", "n2", "n3", "n4"})
        self.assertEqual(len(graph.edges), 4)

        edge_by_pair = {(edge.source_id, edge.target_id): edge for edge in graph.edges.values()}
        self.assertEqual(set(edge_by_pair.keys()), {("n1", "n2"), ("n2", "n3"), ("n3", "n1"), ("n3", "n4")})
        self.assertTrue(all(edge.directed for edge in edge_by_pair.values()))
        self.assertEqual(edge_by_pair[("n1", "n2")].attributes, {})
        self.assertEqual(edge_by_pair[("n2", "n3")].attributes["value"], 2.5)
        self.assertEqual(edge_by_pair[("n3", "n4")].attributes["value"], "connected")

    def test_matrix_missing_source_column_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(
                self._params(
                    "matrix_missing_source_column.csv",
                    csv_format="matrix",
                )
            )

    def test_matrix_missing_target_columns_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(
                self._params(
                    "matrix_missing_target_columns.csv",
                    csv_format="matrix",
                )
            )

    def test_matrix_duplicate_source_row_raises_error(self) -> None:
        with self.assertRaises(CsvParsingError):
            self.plugin.load_graph(
                self._params(
                    "matrix_duplicate_source.csv",
                    csv_format="matrix",
                )
            )

    def test_plugin_works_with_platform_registry(self) -> None:
        registry = PluginRegistry()
        registry.register_data_source(self.plugin)
        loaded_plugin = registry.get_data_source(self.plugin.plugin_id)

        graph = loaded_plugin.load_graph(self._params("edge_list_valid.csv"))
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(len(graph.edges), 2)


if __name__ == "__main__":
    unittest.main()
