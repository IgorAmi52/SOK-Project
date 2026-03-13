from __future__ import annotations

from pathlib import Path

import yaml

from graph_api.contracts.data_source import DataSourcePlugin, PluginParameter
from graph_api.model.graph import Graph

from .errors import YamlInputError
from .parser import YamlGraphParser


class YamlDataSourcePlugin(DataSourcePlugin):
    @property
    def plugin_id(self) -> str:
        return "yaml-data-source"

    @property
    def display_name(self) -> str:
        return "YAML Data Source"

    @property
    def parameters(self) -> list[PluginParameter]:
        return [
            PluginParameter(
                name="file_path",
                description="Path to YAML file that will be parsed into a graph.",
                required=True,
            ),
            PluginParameter(
                name="graph_id",
                description="Optional graph identifier. If omitted, file name is used.",
                required=False,
            ),
            PluginParameter(
                name="id_field",
                description="Optional object id field used for cyclic references (default: @id).",
                required=False,
            ),
            PluginParameter(
                name="reference_fields",
                description=(
                    "Optional comma-separated list of reference field names "
                    "(default: @ref,ref,parent)."
                ),
                required=False,
            ),
        ]

    def load_graph(self, parameter_values: dict[str, str]) -> Graph:
        file_path = parameter_values.get("file_path", "").strip()
        if not file_path:
            raise YamlInputError("Missing required parameter: file_path")

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise YamlInputError(f"YAML file does not exist: {file_path}")

        try:
            with path.open("r", encoding="utf-8") as source_file:
                payload = yaml.safe_load(source_file)
        except yaml.YAMLError as ex:
            raise YamlInputError(
                f"Invalid YAML content in '{file_path}': {ex}") from ex
        except OSError as ex:
            raise YamlInputError(
                f"Unable to read YAML file '{file_path}': {ex}") from ex

        graph_id = parameter_values.get("graph_id", "").strip() or path.stem
        id_field = parameter_values.get("id_field", "").strip() or "@id"
        raw_reference_fields = parameter_values.get(
            "reference_fields", "").strip()
        reference_fields = (
            {item.strip()
             for item in raw_reference_fields.split(",") if item.strip()}
            if raw_reference_fields
            else {"@ref", "ref", "parent"}
        )

        parser = YamlGraphParser(
            id_field=id_field, reference_fields=reference_fields)
        return parser.parse(payload=payload, graph_id=graph_id)
