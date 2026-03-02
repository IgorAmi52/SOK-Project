from __future__ import annotations

from graph_api.contracts.visualizer import VisualizerPlugin
from graph_api.model.graph import Graph

from .renderer import SimpleGraphRenderer


class SimpleVisualizerPlugin(VisualizerPlugin):
    """Simple visualizer plugin that renders nodes as circles with labels.

    This plugin provides a minimal visualization of the graph structure,
    displaying each node as a circle with its ID or name label. It uses
    D3.js force-directed layout for automatic node positioning.
    """

    def __init__(self) -> None:
        self._renderer = SimpleGraphRenderer()

    @property
    def plugin_id(self) -> str:
        return "simple-visualizer"

    @property
    def display_name(self) -> str:
        return "Simple Visualizer"

    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        """Render the graph as an HTML string.

        Args:
            graph: The graph model to visualize.
            selected_node_id: Optional ID of node to highlight as selected.

        Returns:
            HTML string containing SVG and JavaScript for D3.js visualization.
        """
        return self._renderer.render(graph, selected_node_id)
