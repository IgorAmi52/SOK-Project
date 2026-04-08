from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from pathlib import Path

from graph_api.model.edge import Edge
from graph_api.model.graph import Graph
from graph_api.model.node import Node

from .errors import CsvParameterError, CsvParsingError
from .models import CsvLoadConfig, CsvRows, ParsedGraphData
from .strategies import (
    AdjacencyListCsvStrategy,
    CsvFormatStrategy,
    EdgeListCsvStrategy,
    MatrixCsvStrategy,
)


# Pattern: Template Method — defines the skeleton of the CSV parsing algorithm; subclasses override individual steps
class CsvParsingPipeline(ABC):
    """Template Method pipeline for converting CSV input into Graph."""

    def execute(self, parameter_values: dict[str, str]) -> Graph:
        """Run the full pipeline: load, read, parse, build, validate.

        Args:
            parameter_values: Raw string parameters from the plugin caller.

        Returns:
            A fully constructed and validated Graph.
        """
        config = self.load(parameter_values)
        csv_rows = self.read(config)
        parsed_graph = self.parse(csv_rows, config)
        graph = self.build(parsed_graph, config)
        self.validate(graph, config)
        return graph

    @abstractmethod
    def load(self, parameter_values: dict[str, str]) -> CsvLoadConfig:
        raise NotImplementedError

    @abstractmethod
    def read(self, config: CsvLoadConfig) -> CsvRows:
        raise NotImplementedError

    @abstractmethod
    def parse(self, csv_rows: CsvRows, config: CsvLoadConfig) -> ParsedGraphData:
        raise NotImplementedError

    @abstractmethod
    def build(self, parsed_graph: ParsedGraphData, config: CsvLoadConfig) -> Graph:
        raise NotImplementedError

    @abstractmethod
    def validate(self, graph: Graph, config: CsvLoadConfig) -> None:
        raise NotImplementedError


class DefaultCsvParsingPipeline(CsvParsingPipeline):
    """Concrete pipeline that validates parameters, reads CSV rows, delegates
    format-specific parsing to a strategy, and builds the Graph model.
    """

    def __init__(self, strategies: list[CsvFormatStrategy] | None = None) -> None:
        resolved_strategies = strategies or [
            EdgeListCsvStrategy(),
            AdjacencyListCsvStrategy(),
            MatrixCsvStrategy(),
        ]
        self._strategies: dict[str, CsvFormatStrategy] = {
            strategy.format_name: strategy for strategy in resolved_strategies
        }

    def load(self, parameter_values: dict[str, str]) -> CsvLoadConfig:
        """Validate raw parameters and resolve the file path.

        Args:
            parameter_values: Raw string parameters from the caller.

        Returns:
            A validated CsvLoadConfig.

        Raises:
            CsvParameterError: If required parameters are missing or invalid.
        """
        file_path_raw = parameter_values.get("file_path", "").strip()
        if file_path_raw == "":
            raise CsvParameterError("Missing required parameter 'file_path'.")

        format_name = parameter_values.get("format", "").strip().lower()
        if format_name == "":
            raise CsvParameterError("Missing required parameter 'format'.")
        if format_name not in self._strategies:
            supported = ", ".join(sorted(self._strategies.keys()))
            raise CsvParameterError(
                f"Unsupported CSV format '{format_name}'. Supported formats: {supported}."
            )

        delimiter = parameter_values.get("delimiter", ",").strip() or ","
        if len(delimiter) != 1:
            raise CsvParameterError("Parameter 'delimiter' must be a single character.")

        file_path = Path(file_path_raw).expanduser()
        if not file_path.exists():
            raise CsvParameterError(f"CSV file '{file_path}' does not exist.")
        if not file_path.is_file():
            raise CsvParameterError(f"CSV path '{file_path}' is not a file.")

        graph_id = parameter_values.get("graph_id", "").strip() or file_path.stem

        return CsvLoadConfig(
            file_path=file_path,
            format_name=format_name,
            delimiter=delimiter,
            graph_id=graph_id,
        )

    def read(self, config: CsvLoadConfig) -> CsvRows:
        """Read and normalise the CSV file into header names and row dicts.

        Args:
            config: Validated load configuration.

        Returns:
            A CsvRows instance containing field names and data rows.

        Raises:
            CsvParsingError: If the file has no header or no data rows.
        """
        with config.file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=config.delimiter)
            if not reader.fieldnames:
                raise CsvParsingError("CSV file must contain a header row.")

            fieldnames = tuple(name.strip() for name in reader.fieldnames if name and name.strip())
            if not fieldnames:
                raise CsvParsingError("CSV header row is empty.")

            rows: list[dict[str, str]] = []
            for row in reader:
                normalized_row: dict[str, str] = {}
                for key, value in row.items():
                    if key is None:
                        continue
                    normalized_row[key.strip()] = "" if value is None else value.strip()
                if any(cell != "" for cell in normalized_row.values()):
                    rows.append(normalized_row)

        if not rows:
            raise CsvParsingError("CSV file does not contain any non-empty data rows.")

        return CsvRows(fieldnames=fieldnames, rows=rows)

    def parse(self, csv_rows: CsvRows, config: CsvLoadConfig) -> ParsedGraphData:
        """Delegate row parsing to the format-specific strategy.

        Args:
            csv_rows: Normalised CSV rows.
            config: Validated load configuration.

        Returns:
            Intermediate ParsedGraphData ready for graph construction.
        """
        strategy = self._strategies[config.format_name]
        return strategy.parse_rows(csv_rows)

    def build(self, parsed_graph: ParsedGraphData, config: CsvLoadConfig) -> Graph:
        """Construct a Graph from parsed nodes and edges.

        Args:
            parsed_graph: Intermediate parsed data.
            config: Validated load configuration.

        Returns:
            A fully populated Graph instance.
        """
        graph = Graph(
            graph_id=config.graph_id,
            directed_default=True,
            allow_cycles=True,
        )

        for node_id, attributes in parsed_graph.node_attributes.items():
            node = Node(node_id=node_id)
            for attr_name, attr_value in attributes.items():
                node.set_attribute(attr_name, attr_value)
            graph.add_node(node)

        for edge_data in parsed_graph.edges:
            edge = Edge(
                edge_id=edge_data.edge_id,
                source_id=edge_data.source_id,
                target_id=edge_data.target_id,
                directed=edge_data.directed,
            )
            for attr_name, attr_value in edge_data.attributes.items():
                edge.set_attribute(attr_name, attr_value)
            graph.add_edge(edge)

        return graph

    def validate(self, graph: Graph, config: CsvLoadConfig) -> None:
        """Verify that the graph contains at least one node and one edge.

        Args:
            graph: The graph to validate.
            config: Validated load configuration.

        Raises:
            CsvParsingError: If the graph has no nodes or no edges.
        """
        if len(graph.nodes) == 0:
            raise CsvParsingError("Parsed graph contains no nodes.")
        if len(graph.edges) == 0:
            raise CsvParsingError("Parsed graph contains no edges.")
