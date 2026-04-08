from __future__ import annotations

from graph_api.contracts.visualizer import VisualizerPlugin
from graph_api.model.graph import Graph

from .renderer import BlockGraphRenderer


class BlockVisualizerPlugin(VisualizerPlugin):
    """Visualizer plugin that renders a graph as an interactive HTML block diagram."""

    def __init__(self) -> None:
        self._renderer = BlockGraphRenderer()

    @property
    def plugin_id(self) -> str:
        return "block-visualizer"

    @property
    def display_name(self) -> str:
        return "Block Visualizer"

    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        """Render the graph to an HTML string.

        Args:
            graph: The graph to visualise.
            selected_node_id: Optional node to highlight.

        Returns:
            An HTML string containing the block-diagram visualisation.
        """
        return self._renderer.render(graph, selected_node_id)
