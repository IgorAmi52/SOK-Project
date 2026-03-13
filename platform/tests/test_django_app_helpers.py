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
from graph_platform.core.workspace import Workspace, WorkspaceManager
from graph_platform.django_app import views


def _build_workspace(workspace_id: str, source_plugin_id: str) -> Workspace:
    graph = Graph(graph_id=f"g-{workspace_id}")
    return Workspace(
        workspace_id=workspace_id,
        source_plugin_id=source_plugin_id,
        source_parameters={"file_path": "sample.json"},
        base_graph=graph,
        current_graph=graph,
    )


class WorkspaceHelpersTests(unittest.TestCase):
    def setUp(self) -> None:
        views._WORKSPACE_META.clear()
        views._WORKSPACE_ORDER.clear()

    def test_resolve_active_workspace_id_prefers_requested(self) -> None:
        manager = WorkspaceManager()
        manager.add(_build_workspace("ws-1", "json-data-source"))
        manager.add(_build_workspace("ws-2", "csv_data_source"))
        views._WORKSPACE_ORDER.extend(["ws-1", "ws-2"])

        resolved = views._resolve_active_workspace_id("ws-2", manager)
        self.assertEqual(resolved, "ws-2")

    def test_resolve_active_workspace_id_falls_back_to_first(self) -> None:
        manager = WorkspaceManager()
        manager.add(_build_workspace("ws-1", "json-data-source"))
        views._WORKSPACE_ORDER.append("ws-1")

        resolved = views._resolve_active_workspace_id("", manager)
        self.assertEqual(resolved, "ws-1")

    def test_build_workspace_items_marks_active_workspace(self) -> None:
        manager = WorkspaceManager()
        manager.add(_build_workspace("ws-1", "json-data-source"))
        manager.add(_build_workspace("ws-2", "csv_data_source"))
        views._WORKSPACE_ORDER.extend(["ws-1", "ws-2"])
        views._WORKSPACE_META["ws-1"] = {
            "name": "Workspace One",
            "visualizer_id": "simple-visualizer",
            "search_query": "",
            "filter_query": "",
        }
        views._WORKSPACE_META["ws-2"] = {
            "name": "Workspace Two",
            "visualizer_id": "simple-visualizer",
            "search_query": "",
            "filter_query": "",
        }

        items = views._build_workspace_items(manager, active_workspace_id="ws-2")
        self.assertEqual(len(items), 2)
        self.assertFalse(items[0]["is_active"])
        self.assertTrue(items[1]["is_active"])


if __name__ == "__main__":
    unittest.main()
