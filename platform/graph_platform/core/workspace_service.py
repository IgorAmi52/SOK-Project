from __future__ import annotations

from graph_api.model.graph import Graph

from .graph_service import GraphService
from .query_parser import parse_filter_condition, parse_search_query
from .workspace import Workspace


class WorkspaceService:
    def __init__(self, graph_service: GraphService | None = None) -> None:
        self._graph_service = graph_service or GraphService()

    def apply_filter(self, workspace: Workspace, filter_text: str) -> Graph:
        condition = parse_filter_condition(
            filter_text, workspace.current_graph)
        next_graph = self._graph_service.filter_graph(
            workspace.current_graph,
            condition,
            subgraph_id=self._next_subgraph_id(workspace, "filter"),
        )
        workspace.current_graph = next_graph
        workspace.applied_filters.append(condition)
        return next_graph

    def apply_search(self, workspace: Workspace, search_text: str) -> Graph:
        query = parse_search_query(search_text)
        next_graph = self._graph_service.search_graph(
            workspace.current_graph,
            query,
            subgraph_id=self._next_subgraph_id(workspace, "search"),
        )
        workspace.current_graph = next_graph
        workspace.applied_searches.append(query)
        return next_graph

    def reset_graph(self, workspace: Workspace) -> Graph:
        workspace.current_graph = self._clone_graph(workspace.base_graph)
        workspace.applied_filters.clear()
        workspace.applied_searches.clear()
        return workspace.current_graph

    def _next_subgraph_id(self, workspace: Workspace, operation_name: str) -> str:
        sequence = len(workspace.applied_filters) + \
            len(workspace.applied_searches) + 1
        return f"{workspace.workspace_id}:{operation_name}:{sequence}"

    def _clone_graph(self, graph: Graph) -> Graph:
        return graph.create_subgraph(
            set(graph.nodes.keys()),
            subgraph_id=graph.graph_id,
        )
