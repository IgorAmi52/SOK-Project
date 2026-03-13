from __future__ import annotations

from graph_api.contracts.visualizer import VisualizerPlugin
from graph_api.model.graph import Graph

from .renderer import BlockGraphRenderer


class BlockVisualizerPlugin(VisualizerPlugin):
    def __init__(self) -> None:
        self._renderer = BlockGraphRenderer()

    @property
    def plugin_id(self) -> str:
        return "block-visualizer"

    @property
    def display_name(self) -> str:
        return "Block Visualizer"

    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        return self._renderer.render(graph, selected_node_id)
