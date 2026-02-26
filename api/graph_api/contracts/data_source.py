from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from graph_api.model.graph import Graph


@dataclass(slots=True, frozen=True)
class PluginParameter:
    name: str
    description: str
    required: bool = True


class DataSourcePlugin(ABC):
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @property
    @abstractmethod
    def parameters(self) -> list[PluginParameter]:
        pass

    @abstractmethod
    def load_graph(self, parameter_values: dict[str, str]) -> Graph:
        pass
