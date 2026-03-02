from __future__ import annotations

import json
import re
from datetime import date

import pytest

from graph_api.model.edge import Edge
from graph_api.model.graph import Graph
from graph_api.model.node import Node
from simple_visualizer import SimpleVisualizerPlugin
from simple_visualizer.renderer import SimpleGraphRenderer


@pytest.fixture
def sample_graph() -> Graph:
    """Create a sample graph for testing."""
    graph = Graph(graph_id="test-graph", directed_default=True)

    node1 = Node(node_id="n1")
    node1.set_attribute("name", "Alice")
    node1.set_attribute("age", 30)

    node2 = Node(node_id="n2")
    node2.set_attribute("name", "Bob")
    node2.set_attribute("age", 25)

    node3 = Node(node_id="n3")
    node3.set_attribute("name", "Charlie")
    node3.set_attribute("birth_date", date(1990, 5, 15))

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)

    edge1 = Edge(edge_id="e1", source_id="n1", target_id="n2", directed=True)
    edge1.set_attribute("relationship", "friend")

    edge2 = Edge(edge_id="e2", source_id="n2", target_id="n3", directed=False)

    graph.add_edge(edge1)
    graph.add_edge(edge2)

    return graph


@pytest.fixture
def empty_graph() -> Graph:
    """Create an empty graph."""
    return Graph(graph_id="empty-graph")


class TestSimpleVisualizerPlugin:
    """Tests for SimpleVisualizerPlugin."""

    def test_plugin_id(self) -> None:
        plugin = SimpleVisualizerPlugin()
        assert plugin.plugin_id == "simple-visualizer"

    def test_display_name(self) -> None:
        plugin = SimpleVisualizerPlugin()
        assert plugin.display_name == "Simple Visualizer"

    def test_render_returns_string(self, sample_graph: Graph) -> None:
        plugin = SimpleVisualizerPlugin()
        result = plugin.render(sample_graph)
        assert isinstance(result, str)

    def test_render_contains_svg(self, sample_graph: Graph) -> None:
        plugin = SimpleVisualizerPlugin()
        result = plugin.render(sample_graph)
        assert "<svg" in result
        assert "simple-visualizer-svg" in result

    def test_render_contains_d3_code(self, sample_graph: Graph) -> None:
        plugin = SimpleVisualizerPlugin()
        result = plugin.render(sample_graph)
        assert "d3.forceSimulation" in result
        assert "d3.forceLink" in result

    def test_render_with_selected_node(self, sample_graph: Graph) -> None:
        plugin = SimpleVisualizerPlugin()
        result = plugin.render(sample_graph, selected_node_id="n1")
        assert '"n1"' in result

    def test_render_empty_graph(self, empty_graph: Graph) -> None:
        plugin = SimpleVisualizerPlugin()
        result = plugin.render(empty_graph)
        assert isinstance(result, str)
        assert "[]" in result  # Empty nodes array


class TestSimpleGraphRenderer:
    """Tests for SimpleGraphRenderer."""

    def test_render_includes_all_nodes(self, sample_graph: Graph) -> None:
        renderer = SimpleGraphRenderer()
        result = renderer.render(sample_graph)

        # Extract nodes JSON from the rendered output
        nodes_match = re.search(r'const nodes = (\[.*?\]);', result, re.DOTALL)
        assert nodes_match is not None
        nodes_data = json.loads(nodes_match.group(1))

        node_ids = {n["id"] for n in nodes_data}
        assert node_ids == {"n1", "n2", "n3"}

    def test_render_includes_all_edges(self, sample_graph: Graph) -> None:
        renderer = SimpleGraphRenderer()
        result = renderer.render(sample_graph)

        # Extract links JSON from the rendered output
        links_match = re.search(r'const links = (\[.*?\]);', result, re.DOTALL)
        assert links_match is not None
        links_data = json.loads(links_match.group(1))

        assert len(links_data) == 2

    def test_node_labels_use_name_attribute(self, sample_graph: Graph) -> None:
        renderer = SimpleGraphRenderer()
        result = renderer.render(sample_graph)

        nodes_match = re.search(r'const nodes = (\[.*?\]);', result, re.DOTALL)
        assert nodes_match is not None
        nodes_data = json.loads(nodes_match.group(1))

        labels = {n["label"] for n in nodes_data}
        assert "Alice" in labels
        assert "Bob" in labels
        assert "Charlie" in labels

    def test_date_attributes_serialized(self, sample_graph: Graph) -> None:
        renderer = SimpleGraphRenderer()
        result = renderer.render(sample_graph)

        # Date should be serialized as ISO format string
        assert "1990-05-15" in result

    def test_directed_edges_have_marker(self, sample_graph: Graph) -> None:
        renderer = SimpleGraphRenderer()
        result = renderer.render(sample_graph)

        # Check for arrow marker definition
        assert "arrowhead" in result
        assert 'marker-end' in result

    def test_graph_id_sanitized(self) -> None:
        graph = Graph(graph_id="my-test graph")
        graph.add_node(Node(node_id="n1"))

        renderer = SimpleGraphRenderer()
        result = renderer.render(graph)

        # Spaces and dashes should be replaced with underscores
        assert "my_test_graph" in result
