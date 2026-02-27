from __future__ import annotations

from graph_api.contracts.data_source import DataSourcePlugin, PluginParameter
from graph_api.model.graph import Graph

from .errors import CsvParameterError
from .pipeline import CsvParsingPipeline, DefaultCsvParsingPipeline


class CsvDataSourcePlugin(DataSourcePlugin):
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
        if not isinstance(parameter_values, dict):
            raise CsvParameterError("Parameter values must be provided as a dictionary.")
        return self._pipeline.execute(parameter_values)
