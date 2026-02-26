from __future__ import annotations

from abc import ABC, abstractmethod

from graph_api.model.graph import Graph


class VisualizerPlugin(ABC):
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def render(self, graph: Graph, selected_node_id: str | None = None) -> str:
        pass
