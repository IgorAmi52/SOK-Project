from __future__ import annotations

from abc import ABC, abstractmethod

from graph_api.model.graph import Graph


class VisualizerPlugin(ABC):
    """Abstract contract for plugins that render a graph to a visual format."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for this visualizer plugin."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in the UI."""

    @abstractmethod
    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        """Render the graph and return the result as an HTML/SVG string.

        Args:
            graph: The graph to render.
            selected_node_id: Optional node to highlight in the output.

        Returns:
            A string containing the rendered visualization.
        """
