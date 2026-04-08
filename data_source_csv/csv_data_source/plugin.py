from __future__ import annotations

from graph_api.contracts.data_source import DataSourcePlugin, PluginParameter
from graph_api.model.graph import Graph

from .errors import CsvParameterError
from .pipeline import CsvParsingPipeline, DefaultCsvParsingPipeline


class CsvDataSourcePlugin(DataSourcePlugin):
    """Data-source plugin that loads a graph from a CSV file."""

    def __init__(self, pipeline: CsvParsingPipeline | None = None) -> None:
        self._pipeline = pipeline or DefaultCsvParsingPipeline()

    @property
    def plugin_id(self) -> str:
        return "csv_data_source"

    @property
    def display_name(self) -> str:
        return "CSV Data Source"

    @property
    def parameters(self) -> list[PluginParameter]:
        return [
            PluginParameter(
                name="file_path",
                description="Path to the CSV file that should be loaded.",
                required=True,
            ),
            PluginParameter(
                name="format",
                description="CSV graph format: edge_list, adjacency_list, matrix.",
                required=True,
                choices=("edge_list", "adjacency_list", "matrix"),
            ),
            PluginParameter(
                name="delimiter",
                description="Optional CSV delimiter (single character, default ',').",
                required=False,
            ),
            PluginParameter(
                name="graph_id",
                description="Optional graph identifier (defaults to CSV filename).",
                required=False,
            ),
        ]

    def load_graph(self, parameter_values: dict[str, str]) -> Graph:
        """Execute the CSV parsing pipeline and return the resulting graph.

        Args:
            parameter_values: Plugin parameters including ``file_path``,
                ``format``, and optional ``delimiter`` and ``graph_id``.

        Returns:
            A Graph built from the CSV content.

        Raises:
            CsvParameterError: If parameter values are invalid.
        """
        if not isinstance(parameter_values, dict):
            raise CsvParameterError("Parameter values must be provided as a dictionary.")
        return self._pipeline.execute(parameter_values)
