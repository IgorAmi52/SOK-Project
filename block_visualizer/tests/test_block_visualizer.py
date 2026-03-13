from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for package_dir in ("api", "block_visualizer"):
    resolved = PROJECT_ROOT / package_dir
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))

from block_visualizer import BlockVisualizerPlugin
from block_visualizer.renderer import BlockGraphRenderer
from graph_api.model.edge import Edge
from graph_api.model.graph import Graph
from graph_api.model.node import Node


def build_graph() -> Graph:
    graph = Graph(graph_id="workspace:demo:block", directed_default=True)

    node_a = Node(node_id="n1")
    node_a.set_attribute("name", "Alice")
    node_a.set_attribute("age", 30)
    node_a.set_attribute("joined", date(2024, 1, 11))

    node_b = Node(node_id="n2")
    node_b.set_attribute("name", "Bob")
    node_b.set_attribute("score", 91.5)

    graph.add_node(node_a)
    graph.add_node(node_b)

    edge = Edge(edge_id="e1", source_id="n1", target_id="n2", directed=True)
    edge.set_attribute("relation", "knows")
    graph.add_edge(edge)
    return graph


class BlockVisualizerPluginTests(unittest.TestCase):
    def test_plugin_identity(self) -> None:
        plugin = BlockVisualizerPlugin()
        self.assertEqual(plugin.plugin_id, "block-visualizer")
        self.assertEqual(plugin.display_name, "Block Visualizer")

    def test_render_returns_html_string(self) -> None:
        plugin = BlockVisualizerPlugin()
        html = plugin.render(build_graph())
        self.assertIsInstance(html, str)
        self.assertIn("block-visualizer-container", html)
        self.assertIn('node.append("rect")', html)


class BlockGraphRendererTests(unittest.TestCase):
    def test_date_is_serialized_as_iso(self) -> None:
        renderer = BlockGraphRenderer()
        html = renderer.render(build_graph())
        self.assertIn("2024-01-11", html)

    def test_nodes_json_contains_all_nodes(self) -> None:
        renderer = BlockGraphRenderer()
        html = renderer.render(build_graph())

        nodes_match = re.search(r"const nodes = (\[.*?\]);", html, re.DOTALL)
        self.assertIsNotNone(nodes_match)
        nodes_data = json.loads(nodes_match.group(1))
        node_ids = {node["id"] for node in nodes_data}
        self.assertEqual(node_ids, {"n1", "n2"})

    def test_graph_id_is_sanitized(self) -> None:
        renderer = BlockGraphRenderer()
        html = renderer.render(build_graph())
        self.assertIn("workspace_demo_block", html)


if __name__ == "__main__":
    unittest.main()
