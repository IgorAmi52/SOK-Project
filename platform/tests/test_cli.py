from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for package_dir in ("api", "platform"):
    resolved = PROJECT_ROOT / package_dir
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))

from graph_api.model.graph import Graph
from graph_api.model.node import Node
from graph_platform.core.cli import CliCommandError, CliCommandExecutor
from graph_platform.core.workspace import Workspace


def _build_workspace() -> Workspace:
    graph = Graph(graph_id="cli-base")
    node_a = Node(node_id="n1")
    node_a.set_attribute("name", "Alice")
    node_b = Node(node_id="n2")
    node_b.set_attribute("name", "Bob")
    graph.add_node(node_a)
    graph.add_node(node_b)
    return Workspace(
        workspace_id="ws-cli",
        source_plugin_id="test",
        source_parameters={},
        base_graph=graph,
        current_graph=graph,
    )


class CliCommandExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = _build_workspace()
        self.executor = CliCommandExecutor()

    def test_create_and_edit_node(self) -> None:
        self.executor.execute(
            self.workspace,
            "create node --id=n3 --property name=Charlie --property age=31",
        )
        self.assertIn("n3", self.workspace.current_graph.nodes)

        self.executor.execute(self.workspace, "edit node --id=n3 --property age=32")
        self.assertEqual(self.workspace.current_graph.nodes["n3"].attributes["age"], 32)

    def test_create_edge_requires_existing_nodes(self) -> None:
        with self.assertRaises(CliCommandError):
            self.executor.execute(
                self.workspace,
                "create edge --id=e1 --source=n1 --target=missing --directed=true",
            )

    def test_search_and_filter_commands(self) -> None:
        result_search = self.executor.execute(self.workspace, "search Alice")
        self.assertEqual(result_search.operation, "search")
        self.assertEqual(len(self.workspace.current_graph.nodes), 1)

        self.executor.execute(self.workspace, "clear")
        self.executor.execute(self.workspace, "create node --id=n4 --property age=20")
        result_filter = self.executor.execute(self.workspace, "filter age>=20")
        self.assertEqual(result_filter.operation, "filter")
        self.assertEqual(len(self.workspace.current_graph.nodes), 1)

    def test_clear_resets_current_graph(self) -> None:
        result = self.executor.execute(self.workspace, "clear")
        self.assertEqual(result.operation, "clear")
        self.assertEqual(len(self.workspace.current_graph.nodes), 0)

    def test_missing_required_option_raises_error(self) -> None:
        with self.assertRaises(CliCommandError):
            self.executor.execute(self.workspace, "create node --property name=NoId")


if __name__ == "__main__":
    unittest.main()
