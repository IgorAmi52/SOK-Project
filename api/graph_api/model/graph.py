from __future__ import annotations

from dataclasses import dataclass, field

from .edge import Edge
from .errors import GraphConstraintError, GraphValidationError
from .node import Node


@dataclass(slots=True)
class Graph:
    graph_id: str
    directed_default: bool = True
    allow_cycles: bool = True
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        if node.node_id in self.nodes:
            raise GraphValidationError(f"Node '{node.node_id}' already exists.")
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.edge_id in self.edges:
            raise GraphValidationError(f"Edge '{edge.edge_id}' already exists.")
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise GraphValidationError("Both source and target nodes must exist before adding edge.")
        self.edges[edge.edge_id] = edge

    def remove_node(self, node_id: str) -> None:
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
        self.edges.pop(edge_id, None)

    def get_outgoing_edges(self, node_id: str) -> list[Edge]:
        return [edge for edge in self.edges.values() if edge.source_id == node_id]

    def get_incoming_edges(self, node_id: str) -> list[Edge]:
        return [edge for edge in self.edges.values() if edge.target_id == node_id]

    def create_subgraph(self, node_ids: set[str], subgraph_id: str) -> Graph:
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
