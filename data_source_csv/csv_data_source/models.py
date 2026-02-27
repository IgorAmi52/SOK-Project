from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from graph_api.model.attribute import AttributeValue


@dataclass(slots=True, frozen=True)
class CsvLoadConfig:
    file_path: Path
    format_name: str
    delimiter: str
    graph_id: str


@dataclass(slots=True, frozen=True)
class CsvRows:
    fieldnames: tuple[str, ...]
    rows: list[dict[str, str]]


@dataclass(slots=True, frozen=True)
class ParsedEdge:
    edge_id: str
    source_id: str
    target_id: str
    directed: bool
    attributes: dict[str, AttributeValue]


@dataclass(slots=True)
class ParsedGraphData:
    node_attributes: dict[str, dict[str, AttributeValue]] = field(default_factory=dict)
    edges: list[ParsedEdge] = field(default_factory=list)
