from __future__ import annotations

from dataclasses import dataclass, field

from graph_api.model.graph import Graph
from graph_api.query.filters import FilterCondition
from graph_api.query.search import SearchQuery


@dataclass(slots=True)
class Workspace:
    """Holds the graph state and query history for a single user session."""
    workspace_id: str
    source_plugin_id: str
    source_parameters: dict[str, str]
    base_graph: Graph
    current_graph: Graph
    applied_filters: list[FilterCondition] = field(default_factory=list)
    applied_searches: list[SearchQuery] = field(default_factory=list)


class WorkspaceManager:
    """In-memory store for active workspaces, keyed by workspace ID."""

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}

    def add(self, workspace: Workspace) -> None:
        """Add or replace a workspace in the store.

        Args:
            workspace: The workspace to store.
        """
        self._workspaces[workspace.workspace_id] = workspace

    def get(self, workspace_id: str) -> Workspace:
        """Retrieve a workspace by its identifier.

        Args:
            workspace_id: Unique identifier of the workspace.

        Returns:
            The matching Workspace instance.
        """
        return self._workspaces[workspace_id]

    def remove(self, workspace_id: str) -> Workspace | None:
        """Remove and return a workspace, or ``None`` if not found.

        Args:
            workspace_id: Unique identifier of the workspace to remove.

        Returns:
            The removed Workspace, or None if the ID was not present.
        """
        return self._workspaces.pop(workspace_id, None)

    def has(self, workspace_id: str) -> bool:
        """Check whether a workspace with the given ID exists.

        Args:
            workspace_id: Unique identifier to look up.

        Returns:
            True if the workspace exists, False otherwise.
        """
        return workspace_id in self._workspaces

    def list_all(self) -> list[Workspace]:
        """Return all stored workspaces."""
        return list(self._workspaces.values())
