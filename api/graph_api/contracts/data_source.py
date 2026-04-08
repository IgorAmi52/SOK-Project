from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from graph_api.model.graph import Graph


@dataclass(slots=True, frozen=True)
class PluginParameter:
    """Descriptor for a single parameter accepted by a data-source plugin."""

    name: str
    description: str
    required: bool = True
    choices: tuple[str, ...] = ()


# Pattern: Strategy — DataSourcePlugin/VisualizerPlugin define the contract;
# concrete plugins implement strategy-specific behavior
class DataSourcePlugin(ABC):
    """Abstract contract for plugins that load graphs from external sources."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for this plugin."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in the UI."""

    @property
    @abstractmethod
    def parameters(self) -> list[PluginParameter]:
        """Parameters the user must supply to load a graph."""

    @abstractmethod
    def load_graph(self, parameter_values: dict[str, str]) -> Graph:
        """Load and return a graph using the supplied parameter values.

        Args:
            parameter_values: Mapping of parameter names to user-supplied values.

        Returns:
            A fully constructed Graph instance.
        """
