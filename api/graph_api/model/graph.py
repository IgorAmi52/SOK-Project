from __future__ import annotations

from dataclasses import dataclass, field

from .edge import Edge
from .errors import GraphConstraintError, GraphValidationError
from .node import Node


@dataclass(slots=True)
class Graph:
    """Directed or undirected graph composed of nodes and edges."""

    graph_id: str
    directed_default: bool = True
    allow_cycles: bool = True
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        """Add a node to the graph.

        Args:
            node: The node to add.

        Raises:
            GraphValidationError: If a node with the same id already exists.
        """
        if node.node_id in self.nodes:
            raise GraphValidationError(f"Node '{node.node_id}' already exists.")
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph.

        Args:
            edge: The edge to add.

        Raises:
            GraphValidationError: If the edge id is duplicate or endpoints are missing.
            GraphConstraintError: If the edge would create a cycle in an acyclic graph.
        """
        if edge.edge_id in self.edges:
            raise GraphValidationError(f"Edge '{edge.edge_id}' already exists.")
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise GraphValidationError("Both source and target nodes must exist before adding edge.")
        if not self.allow_cycles and self._creates_cycle(edge):
            raise GraphConstraintError(
                f"Adding edge '{edge.edge_id}' would create a cycle in graph '{self.graph_id}'."
            )
        self.edges[edge.edge_id] = edge

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the graph.

        Args:
            node_id: Identifier of the node to remove.

        Raises:
            GraphConstraintError: If the node still has connected edges.
        """
        connected = [
            edge.edge_id
            for edge in self.edges.values()
            if edge.source_id == node_id or edge.target_id == node_id
        ]
        if connected:
            raise GraphConstraintError(
                f"Node '{node_id}' is connected to edges {connected}. Remove those edges first."
            )
        self.nodes.pop(node_id, None)

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the graph by its id.

        Args:
            edge_id: Identifier of the edge to remove.
        """
        self.edges.pop(edge_id, None)

    def get_outgoing_edges(self, node_id: str) -> list[Edge]:
        """Return all edges originating from the given node.

        Args:
            node_id: Source node identifier.
        """
        return [edge for edge in self.edges.values() if edge.source_id == node_id]

    def get_incoming_edges(self, node_id: str) -> list[Edge]:
        """Return all edges targeting the given node.

        Args:
            node_id: Target node identifier.
        """
        return [edge for edge in self.edges.values() if edge.target_id == node_id]

    def create_subgraph(self, node_ids: set[str], subgraph_id: str) -> Graph:
        """Create a new graph containing only the specified nodes and their interconnecting edges.

        Args:
            node_ids: Set of node identifiers to include.
            subgraph_id: Identifier for the new subgraph.

        Returns:
            A new Graph instance with copied nodes and edges.
        """
        subgraph = Graph(
            graph_id=subgraph_id,
            directed_default=self.directed_default,
            allow_cycles=self.allow_cycles,
        )
        for node_id in node_ids:
            node = self.nodes.get(node_id)
            if node is not None:
                subgraph.add_node(Node(node_id=node.node_id, attributes=dict(node.attributes)))

        for edge in self.edges.values():
            if edge.source_id in node_ids and edge.target_id in node_ids:
                subgraph.add_edge(
                    Edge(
                        edge_id=edge.edge_id,
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        directed=edge.directed,
                        attributes=dict(edge.attributes),
                    )
                )
        return subgraph

    def _creates_cycle(self, edge: Edge) -> bool:
        if edge.source_id == edge.target_id:
            return True

        if edge.directed:
            return self._path_exists(edge.target_id, edge.source_id, treat_directed=True)
        return self._path_exists(edge.target_id, edge.source_id, treat_directed=False)

    def _path_exists(self, start_id: str, goal_id: str, treat_directed: bool) -> bool:
        if start_id == goal_id:
            return True

        visited: set[str] = set()
        stack = [start_id]

        while stack:
            node_id = stack.pop()
            if node_id == goal_id:
                return True
            if node_id in visited:
                continue
            visited.add(node_id)
            for neighbor_id in self._neighbors(node_id, treat_directed=treat_directed):
                if neighbor_id not in visited:
                    stack.append(neighbor_id)
        return False

    def _neighbors(self, node_id: str, treat_directed: bool) -> list[str]:
        neighbors: list[str] = []
        for edge in self.edges.values():
            if edge.directed:
                if edge.source_id == node_id:
                    neighbors.append(edge.target_id)
                if not treat_directed and edge.target_id == node_id:
                    neighbors.append(edge.source_id)
                continue

            if edge.source_id == node_id:
                neighbors.append(edge.target_id)
            if edge.target_id == node_id:
                neighbors.append(edge.source_id)
        return neighbors
