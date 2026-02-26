from __future__ import annotations

from dataclasses import dataclass, field

from graph_api.model.graph import Graph
from graph_api.query.filters import FilterCondition
from graph_api.query.search import SearchQuery


@dataclass(slots=True)
class Workspace:
    workspace_id: str
    source_plugin_id: str
    source_parameters: dict[str, str]
    base_graph: Graph
    current_graph: Graph
    applied_filters: list[FilterCondition] = field(default_factory=list)
    applied_searches: list[SearchQuery] = field(default_factory=list)


class WorkspaceManager:
    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}

    def add(self, workspace: Workspace) -> None:
        self._workspaces[workspace.workspace_id] = workspace

    def get(self, workspace_id: str) -> Workspace:
        return self._workspaces[workspace_id]

    def list_all(self) -> list[Workspace]:
        return list(self._workspaces.values())
