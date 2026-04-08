from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from graph_api.model.graph import Graph


def _serialize_attribute_value(value: int | str | float | date) -> str | int | float:
    if isinstance(value, date):
        return value.isoformat()
    return value


def _node_title(node_id: str, attributes: dict[str, object]) -> str:
    for key in ("name", "label", "title", "id", "first"):
        if key in attributes:
            return str(attributes[key])
    return node_id


class BlockGraphRenderer:
    """Renders a Graph as an HTML block diagram using Jinja2 templates."""

    def __init__(self) -> None:
        templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        """Produce an HTML string for the given graph.

        Args:
            graph: The graph to render.
            selected_node_id: Optional node to highlight in the output.

        Returns:
            A complete HTML document string.
        """
        nodes_data: list[dict[str, object]] = []
        for node_id, node in graph.nodes.items():
            attributes = {
                attr_name: _serialize_attribute_value(attr_value)
                for attr_name, attr_value in node.attributes.items()
            }
            rows = [f"{name}: {value}" for name, value in attributes.items()][:4]
            nodes_data.append(
                {
                    "id": node_id,
                    "title": _node_title(node_id, attributes),
                    "attributes": attributes,
                    "rows": rows,
                    "height": 42 + (len(rows) * 14),
                    "width": 180,
                }
            )

        edges_data: list[dict[str, object]] = []
        for edge in graph.edges.values():
            attributes = {
                attr_name: _serialize_attribute_value(attr_value)
                for attr_name, attr_value in edge.attributes.items()
            }
            edges_data.append(
                {
                    "id": edge.edge_id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "directed": edge.directed,
                    "attributes": attributes,
                }
            )

        safe_graph_id = re.sub(r"[^0-9A-Za-z_]", "_", graph.graph_id)
        template = self._env.get_template("block_graph.html")
        return template.render(
            graph_id=safe_graph_id,
            nodes_json=json.dumps(nodes_data),
            edges_json=json.dumps(edges_data),
            selected_node_id_json=json.dumps(selected_node_id),
        )
