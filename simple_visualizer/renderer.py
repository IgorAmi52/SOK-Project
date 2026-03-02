from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from graph_api.model.graph import Graph


def _serialize_attribute_value(value: int | str | float | date) -> str | int | float:
    """Convert attribute values to JSON-serializable types."""
    if isinstance(value, date):
        return value.isoformat()
    return value


def _get_node_label(node_id: str, attributes: dict) -> str:
    """Determine display label for a node."""
    for key in ("name", "label", "title", "id", "first"):
        if key in attributes:
            return str(attributes[key])
    return node_id


class SimpleGraphRenderer:
    """Renders a graph to HTML string using D3.js force-directed layout."""

    def __init__(self) -> None:
        templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,
        )

    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        """Generate HTML string for visualizing the graph.

        Args:
            graph: The graph model to render.
            selected_node_id: Optional ID of node to highlight.

        Returns:
            HTML string containing SVG and D3.js code for the graph.
        """
        nodes_data = []
        for node_id, node in graph.nodes.items():
            attrs = {
                k: _serialize_attribute_value(v)
                for k, v in node.attributes.items()
            }
            nodes_data.append({
                "id": node_id,
                "label": _get_node_label(node_id, attrs),
                "attributes": attrs,
            })

        edges_data = []
        for edge in graph.edges.values():
            attrs = {
                k: _serialize_attribute_value(v)
                for k, v in edge.attributes.items()
            }
            edges_data.append({
                "id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "directed": edge.directed,
                "attributes": attrs,
            })

        template = self._env.get_template("simple_graph.html")
        return template.render(
            graph_id=graph.graph_id.replace(" ", "_").replace("-", "_"),
            nodes_json=json.dumps(nodes_data),
            edges_json=json.dumps(edges_data),
            selected_node_id_json=json.dumps(selected_node_id),
            is_directed=graph.directed_default,
        )
