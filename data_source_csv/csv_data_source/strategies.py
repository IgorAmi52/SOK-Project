from __future__ import annotations

from abc import ABC, abstractmethod

from graph_api.model.attribute import AttributeValue

from .errors import CsvParsingError
from .models import CsvRows, ParsedEdge, ParsedGraphData
from .type_inference import infer_attribute_value


class CsvFormatStrategy(ABC):
    @property
    @abstractmethod
    def format_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_rows(self, csv_rows: CsvRows) -> ParsedGraphData:
        raise NotImplementedError


class EdgeListCsvStrategy(CsvFormatStrategy):
    _REQUIRED_COLUMNS = ("source", "target")
    _TRUTHY = {"1", "true", "yes", "y", "t"}
    _FALSY = {"0", "false", "no", "n", "f"}

    @property
    def format_name(self) -> str:
        return "edge_list"

    def parse_rows(self, csv_rows: CsvRows) -> ParsedGraphData:
        missing_columns = [
            column for column in self._REQUIRED_COLUMNS if column not in csv_rows.fieldnames
        ]
        if missing_columns:
            raise CsvParsingError(
                "Edge list CSV is missing required columns: " + ", ".join(missing_columns)
            )

        parsed = ParsedGraphData()
        seen_edge_ids: set[str] = set()
        auto_edge_id = 1

        for row_index, row in enumerate(csv_rows.rows, start=2):
            source_id = self._get_required_cell(row, "source", row_index)
            target_id = self._get_required_cell(row, "target", row_index)

            parsed.node_attributes.setdefault(source_id, {})
            parsed.node_attributes.setdefault(target_id, {})

            parsed.node_attributes[source_id].update(self._extract_prefixed(row, "source_"))
            parsed.node_attributes[target_id].update(self._extract_prefixed(row, "target_"))

            edge_id = row.get("edge_id", "").strip()
            if edge_id == "":
                edge_id = f"e{auto_edge_id}"
                auto_edge_id += 1

            if edge_id in seen_edge_ids:
                raise CsvParsingError(f"Duplicate edge_id '{edge_id}' at row {row_index}.")
            seen_edge_ids.add(edge_id)

            directed_raw = row.get("directed", "").strip()
            directed = True if directed_raw == "" else self._parse_bool(directed_raw, row_index)

            parsed.edges.append(
                ParsedEdge(
                    edge_id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    directed=directed,
                    attributes=self._extract_prefixed(row, "edge_"),
                )
            )

        return parsed

    def _get_required_cell(self, row: dict[str, str], key: str, row_index: int) -> str:
        value = row.get(key, "").strip()
        if value == "":
            raise CsvParsingError(f"Row {row_index} has empty required '{key}' value.")
        return value

    def _extract_prefixed(self, row: dict[str, str], prefix: str) -> dict[str, AttributeValue]:
        attributes: dict[str, AttributeValue] = {}
        for key, value in row.items():
            if not key.startswith(prefix):
                continue
            attr_name = key[len(prefix) :].strip()
            if attr_name == "":
                continue
            if value.strip() == "":
                continue
            attributes[attr_name] = infer_attribute_value(value)
        return attributes

    def _parse_bool(self, value: str, row_index: int) -> bool:
        lowered = value.strip().lower()
        if lowered in self._TRUTHY:
            return True
        if lowered in self._FALSY:
            return False
        raise CsvParsingError(
            f"Row {row_index} contains invalid directed flag '{value}'. "
            "Use true/false, yes/no, 1/0."
        )


class AdjacencyListCsvStrategy(CsvFormatStrategy):
    _REQUIRED_COLUMNS = ("source", "targets")
    _TRUTHY = {"1", "true", "yes", "y", "t"}
    _FALSY = {"0", "false", "no", "n", "f"}

    @property
    def format_name(self) -> str:
        return "adjacency_list"

    def parse_rows(self, csv_rows: CsvRows) -> ParsedGraphData:
        missing_columns = [
            column for column in self._REQUIRED_COLUMNS if column not in csv_rows.fieldnames
        ]
        if missing_columns:
            raise CsvParsingError(
                "Adjacency list CSV is missing required columns: " + ", ".join(missing_columns)
            )

        parsed = ParsedGraphData()
        seen_edge_ids: set[str] = set()
        auto_edge_id = 1

        for row_index, row in enumerate(csv_rows.rows, start=2):
            source_id = self._get_required_cell(row, "source", row_index)
            parsed.node_attributes.setdefault(source_id, {})
            parsed.node_attributes[source_id].update(self._extract_prefixed(row, "source_"))

            directed_raw = row.get("directed", "").strip()
            directed = True if directed_raw == "" else self._parse_bool(directed_raw, row_index)

            targets = self._parse_targets(row.get("targets", ""), row_index=row_index)
            provided_edge_id = row.get("edge_id", "").strip()
            if provided_edge_id != "" and len(targets) > 1:
                raise CsvParsingError(
                    f"Row {row_index} cannot provide one edge_id for multiple targets."
                )

            edge_attributes = self._extract_prefixed(row, "edge_")

            for target_id in targets:
                parsed.node_attributes.setdefault(target_id, {})

                edge_id = provided_edge_id
                if edge_id == "":
                    edge_id = f"e{auto_edge_id}"
                    auto_edge_id += 1

                if edge_id in seen_edge_ids:
                    raise CsvParsingError(f"Duplicate edge_id '{edge_id}' at row {row_index}.")
                seen_edge_ids.add(edge_id)

                parsed.edges.append(
                    ParsedEdge(
                        edge_id=edge_id,
                        source_id=source_id,
                        target_id=target_id,
                        directed=directed,
                        attributes=dict(edge_attributes),
                    )
                )

        return parsed

    def _get_required_cell(self, row: dict[str, str], key: str, row_index: int) -> str:
        value = row.get(key, "").strip()
        if value == "":
            raise CsvParsingError(f"Row {row_index} has empty required '{key}' value.")
        return value

    def _extract_prefixed(self, row: dict[str, str], prefix: str) -> dict[str, AttributeValue]:
        attributes: dict[str, AttributeValue] = {}
        for key, value in row.items():
            if not key.startswith(prefix):
                continue
            attr_name = key[len(prefix) :].strip()
            if attr_name == "":
                continue
            if value.strip() == "":
                continue
            attributes[attr_name] = infer_attribute_value(value)
        return attributes

    def _parse_bool(self, value: str, row_index: int) -> bool:
        lowered = value.strip().lower()
        if lowered in self._TRUTHY:
            return True
        if lowered in self._FALSY:
            return False
        raise CsvParsingError(
            f"Row {row_index} contains invalid directed flag '{value}'. "
            "Use true/false, yes/no, 1/0."
        )

    def _parse_targets(self, raw_targets: str, row_index: int) -> list[str]:
        targets = [target.strip() for target in raw_targets.split("|") if target.strip() != ""]
        if not targets:
            raise CsvParsingError(f"Row {row_index} has no targets in adjacency list.")
        return targets


class MatrixCsvStrategy(CsvFormatStrategy):
    _REQUIRED_ROW_COLUMN = "source"
    _NO_EDGE_LITERALS = {"false", "no", "n", "f"}
    _TRUTHY_EDGE_LITERALS = {"1", "true", "yes", "y", "t"}

    @property
    def format_name(self) -> str:
        return "matrix"

    def parse_rows(self, csv_rows: CsvRows) -> ParsedGraphData:
        if self._REQUIRED_ROW_COLUMN not in csv_rows.fieldnames:
            raise CsvParsingError("Matrix CSV is missing required column: source")

        target_columns = [name for name in csv_rows.fieldnames if name != self._REQUIRED_ROW_COLUMN]
        if not target_columns:
            raise CsvParsingError("Matrix CSV must define at least one target node column.")

        parsed = ParsedGraphData()
        seen_sources: set[str] = set()
        auto_edge_id = 1

        for row_index, row in enumerate(csv_rows.rows, start=2):
            source_id = self._get_required_cell(row, self._REQUIRED_ROW_COLUMN, row_index)
            if source_id in seen_sources:
                raise CsvParsingError(f"Duplicate matrix source node '{source_id}' at row {row_index}.")
            seen_sources.add(source_id)
            parsed.node_attributes.setdefault(source_id, {})

            for target_id in target_columns:
                parsed.node_attributes.setdefault(target_id, {})
                cell_value = row.get(target_id, "").strip()
                if self._is_no_edge_cell(cell_value):
                    continue

                attributes: dict[str, AttributeValue] = {}
                if not self._is_truthy_edge_cell(cell_value):
                    attributes["value"] = infer_attribute_value(cell_value)

                parsed.edges.append(
                    ParsedEdge(
                        edge_id=f"e{auto_edge_id}",
                        source_id=source_id,
                        target_id=target_id,
                        directed=True,
                        attributes=attributes,
                    )
                )
                auto_edge_id += 1

        return parsed

    def _get_required_cell(self, row: dict[str, str], key: str, row_index: int) -> str:
        value = row.get(key, "").strip()
        if value == "":
            raise CsvParsingError(f"Row {row_index} has empty required '{key}' value.")
        return value

    def _is_no_edge_cell(self, raw_value: str) -> bool:
        value = raw_value.strip()
        if value == "":
            return True

        lowered = value.lower()
        if lowered in self._NO_EDGE_LITERALS:
            return True

        inferred = infer_attribute_value(value)
        if isinstance(inferred, bool):
            return not inferred
        if isinstance(inferred, (int, float)) and inferred == 0:
            return True
        return False

    def _is_truthy_edge_cell(self, raw_value: str) -> bool:
        lowered = raw_value.strip().lower()
        return lowered in self._TRUTHY_EDGE_LITERALS
