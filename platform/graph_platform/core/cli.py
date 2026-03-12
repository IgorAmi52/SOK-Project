from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import date

from graph_api.model.attribute import AttributeValue
from graph_api.model.edge import Edge
from graph_api.model.errors import GraphConstraintError, GraphValidationError
from graph_api.model.graph import Graph
from graph_api.model.node import Node

from .errors import QueryValidationError
from .workspace import Workspace
from .workspace_service import WorkspaceService


@dataclass(slots=True, frozen=True)
class CliExecutionResult:
    message: str
    operation: str | None = None
    query: str | None = None


class CliCommandError(ValueError):
    pass


class CliCommandExecutor:
    def __init__(self, workspace_service: WorkspaceService | None = None) -> None:
        self._workspace_service = workspace_service or WorkspaceService()

    def execute(self, workspace: Workspace, command_text: str) -> CliExecutionResult:
        command = command_text.strip()
        if not command:
            raise CliCommandError("Command cannot be empty.")

        tokens = shlex.split(command)
        if not tokens:
            raise CliCommandError("Command cannot be empty.")

        verb = tokens[0].lower()
        try:
            if verb == "help":
                return CliExecutionResult(message=self._help_message())
            if verb == "clear":
                workspace.current_graph = Graph(
                    graph_id=f"{workspace.workspace_id}:clear",
                    directed_default=workspace.current_graph.directed_default,
                    allow_cycles=workspace.current_graph.allow_cycles,
                )
                workspace.applied_filters.clear()
                workspace.applied_searches.clear()
                return CliExecutionResult(message="Graph cleared.", operation="clear")

            if verb in {"search", "filter"}:
                query_text = " ".join(tokens[1:]).strip()
                if not query_text:
                    raise CliCommandError(f"{verb} requires a query.")
                if verb == "search":
                    self._workspace_service.apply_search(workspace, query_text)
                    return CliExecutionResult(
                        message=f"Search applied: {query_text}",
                        operation="search",
                        query=query_text,
                    )
                self._workspace_service.apply_filter(workspace, query_text)
                return CliExecutionResult(
                    message=f"Filter applied: {query_text}",
                    operation="filter",
                    query=query_text,
                )

            if len(tokens) < 2:
                raise CliCommandError("Expected command target: node or edge.")

            entity = tokens[1].lower()
            options = self._parse_options(tokens[2:])

            if verb == "create" and entity == "node":
                node_id = self._require_option(options, "id")
                node = Node(node_id=node_id)
                for name, value in options["properties"].items():
                    node.set_attribute(name, value)
                workspace.current_graph.add_node(node)
                return CliExecutionResult(message=f"Node '{node_id}' created.")

            if verb == "edit" and entity == "node":
                node_id = self._require_option(options, "id")
                node = workspace.current_graph.nodes.get(node_id)
                if node is None:
                    raise CliCommandError(f"Node '{node_id}' does not exist.")
                if not options["properties"]:
                    raise CliCommandError("edit node requires at least one --property.")
                for name, value in options["properties"].items():
                    node.set_attribute(name, value)
                return CliExecutionResult(message=f"Node '{node_id}' updated.")

            if verb == "delete" and entity == "node":
                node_id = self._require_option(options, "id")
                workspace.current_graph.remove_node(node_id)
                return CliExecutionResult(message=f"Node '{node_id}' deleted.")

            if verb == "create" and entity == "edge":
                edge_id = self._require_option(options, "id")
                source_id = self._require_option(options, "source")
                target_id = self._require_option(options, "target")
                directed = self._parse_bool(options.get("directed", "true"))
                edge = Edge(
                    edge_id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    directed=directed,
                )
                for name, value in options["properties"].items():
                    edge.set_attribute(name, value)
                workspace.current_graph.add_edge(edge)
                return CliExecutionResult(message=f"Edge '{edge_id}' created.")

            if verb == "edit" and entity == "edge":
                edge_id = self._require_option(options, "id")
                edge = workspace.current_graph.edges.get(edge_id)
                if edge is None:
                    raise CliCommandError(f"Edge '{edge_id}' does not exist.")
                if not options["properties"]:
                    raise CliCommandError("edit edge requires at least one --property.")
                for name, value in options["properties"].items():
                    edge.set_attribute(name, value)
                return CliExecutionResult(message=f"Edge '{edge_id}' updated.")

            if verb == "delete" and entity == "edge":
                edge_id = self._require_option(options, "id")
                workspace.current_graph.remove_edge(edge_id)
                return CliExecutionResult(message=f"Edge '{edge_id}' deleted.")

            raise CliCommandError(f"Unsupported command: {command_text}")
        except (GraphValidationError, GraphConstraintError, QueryValidationError) as exc:
            raise CliCommandError(str(exc)) from exc

    def _parse_options(self, tokens: list[str]) -> dict[str, object]:
        options: dict[str, object] = {
            "id": "",
            "source": "",
            "target": "",
            "directed": "",
            "properties": {},
        }

        index = 0
        while index < len(tokens):
            token = tokens[index]
            if not token.startswith("--"):
                raise CliCommandError(f"Unexpected token '{token}'.")

            key = token[2:]
            value = ""
            if "=" in key:
                key, value = key.split("=", maxsplit=1)
            else:
                if index + 1 >= len(tokens):
                    raise CliCommandError(f"Missing value for option '--{key}'.")
                value = tokens[index + 1]
                index += 1

            if key == "property":
                property_name, property_value = self._split_property(value)
                options["properties"][property_name] = self._parse_attribute_value(property_value)
            elif key in {"id", "source", "target", "directed"}:
                options[key] = value
            else:
                raise CliCommandError(f"Unsupported option '--{key}'.")

            index += 1

        return options

    def _split_property(self, raw_property: str) -> tuple[str, str]:
        if "=" not in raw_property:
            raise CliCommandError(
                f"Invalid property '{raw_property}'. Expected format --property name=value."
            )
        property_name, property_value = raw_property.split("=", maxsplit=1)
        property_name = property_name.strip()
        property_value = property_value.strip()
        if not property_name:
            raise CliCommandError("Property name cannot be empty.")
        if property_value == "":
            raise CliCommandError("Property value cannot be empty.")
        return property_name, property_value

    def _parse_attribute_value(self, raw_value: str) -> AttributeValue:
        value = raw_value.strip()
        if value.lower() in {"true", "false"}:
            return value.lower()
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value

    def _parse_bool(self, raw_value: str) -> bool:
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        raise CliCommandError(
            f"Invalid boolean value '{raw_value}'. Use true/false, yes/no, or 1/0."
        )

    def _require_option(self, options: dict[str, object], key: str) -> str:
        value = str(options.get(key, "")).strip()
        if not value:
            raise CliCommandError(f"Missing required option '--{key}'.")
        return value

    def _help_message(self) -> str:
        return (
            "Commands: create/edit/delete node, create/edit/delete edge, "
            "search <query>, filter <expr>, clear."
        )
