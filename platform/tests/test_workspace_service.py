from __future__ import annotations
from graph_platform.core.workspace_service import WorkspaceService
from graph_platform.core.workspace import Workspace, WorkspaceManager
from graph_platform.core.errors import QueryValidationError
from graph_api.model.node import Node
from graph_api.model.graph import Graph
from graph_api.model.edge import Edge

import sys
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for package_dir in ("api", "platform"):
    resolved = PROJECT_ROOT / package_dir
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))


def build_sample_graph() -> Graph:
    graph = Graph(graph_id="base")

    alice = Node(node_id="n1")
    alice.set_attribute("name", "Alice")
    alice.set_attribute("age", 30)
    alice.set_attribute("score", 95.5)
    alice.set_attribute("joined", date(2024, 1, 10))

    bob = Node(node_id="n2")
    bob.set_attribute("name", "Bob")
    bob.set_attribute("age", 25)
    bob.set_attribute("score", 88.0)
    bob.set_attribute("joined", date(2023, 5, 5))

    tom = Node(node_id="n3")
    tom.set_attribute("name", "Tom")
    tom.set_attribute("age", 40)
    tom.set_attribute("score", 70.0)
    tom.set_attribute("joined", date(2022, 12, 1))

    graph.add_node(alice)
    graph.add_node(bob)
    graph.add_node(tom)

    graph.add_edge(Edge(edge_id="e1", source_id="n1",
                   target_id="n2", directed=True))
    graph.add_edge(Edge(edge_id="e2", source_id="n2",
                   target_id="n3", directed=True))
    return graph


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_graph = build_sample_graph()
        current_graph = self.base_graph.create_subgraph(
            set(self.base_graph.nodes.keys()),
            subgraph_id=self.base_graph.graph_id,
        )
        self.workspace = Workspace(
            workspace_id="ws-1",
            source_plugin_id="test-plugin",
            source_parameters={},
            base_graph=self.base_graph,
            current_graph=current_graph,
        )
        self.service = WorkspaceService()

    def test_apply_filter_coerces_integer_values(self) -> None:
        result = self.service.apply_filter(self.workspace, "age>=30")

        self.assertEqual(set(result.nodes.keys()), {"n1", "n3"})
        self.assertEqual(
            self.workspace.current_graph.graph_id, "ws-1:filter:1")
        self.assertEqual(len(self.workspace.applied_filters), 1)

    def test_apply_filter_raises_error_for_invalid_integer_value(self) -> None:
        with self.assertRaises(QueryValidationError):
            self.service.apply_filter(self.workspace, "age>=thirty")

    def test_apply_filter_coerces_date_values(self) -> None:
        result = self.service.apply_filter(
            self.workspace, "joined>=2024-01-01")

        self.assertEqual(set(result.nodes.keys()), {"n1"})

    def test_apply_search_uses_current_subgraph(self) -> None:
        self.service.apply_filter(self.workspace, "age>=30")
        result = self.service.apply_search(self.workspace, "tom")

        self.assertEqual(set(result.nodes.keys()), {"n3"})
        self.assertEqual(
            self.workspace.current_graph.graph_id, "ws-1:search:2")
        self.assertEqual(len(self.workspace.applied_searches), 1)

    def test_reset_graph_restores_base_graph_and_clears_history(self) -> None:
        self.service.apply_filter(self.workspace, "age>=30")
        self.service.apply_search(self.workspace, "alice")

        result = self.service.reset_graph(self.workspace)

        self.assertIsNot(result, self.base_graph)
        self.assertEqual(set(self.workspace.current_graph.nodes.keys()), {
                         "n1", "n2", "n3"})
        self.assertEqual(self.workspace.applied_filters, [])
        self.assertEqual(self.workspace.applied_searches, [])

    def test_reset_restores_graph_after_manual_mutation(self) -> None:
        self.workspace.current_graph.remove_edge("e1")
        self.workspace.current_graph.remove_edge("e2")
        self.workspace.current_graph.remove_node("n2")
        self.assertNotIn("n2", self.workspace.current_graph.nodes)
        self.assertIn("n2", self.workspace.base_graph.nodes)

        result = self.service.reset_graph(self.workspace)

        self.assertIn("n2", result.nodes)
        self.assertIn("e1", result.edges)
        self.assertIn("e2", result.edges)


class WorkspaceManagerTests(unittest.TestCase):
    def test_remove_and_has(self) -> None:
        manager = WorkspaceManager()
        graph = build_sample_graph()
        workspace = Workspace(
            workspace_id="ws-remove",
            source_plugin_id="test-plugin",
            source_parameters={},
            base_graph=graph,
            current_graph=graph,
        )

        manager.add(workspace)
        self.assertTrue(manager.has("ws-remove"))

        removed = manager.remove("ws-remove")
        self.assertIsNotNone(removed)
        self.assertFalse(manager.has("ws-remove"))


if __name__ == "__main__":
    unittest.main()
