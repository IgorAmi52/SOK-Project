from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from graph_api.model.edge import Edge
from graph_api.model.errors import GraphValidationError
from graph_api.model.graph import Graph
from graph_api.model.node import Node

from .errors import JsonReferenceResolutionError


PrimitiveValue = int | float | str | bool | None


@dataclass(slots=True)
class _PendingReference:
    source_node_id: str
    relation_name: str
    target_external_id: str
    index: int | None


class JsonGraphParser:
    def __init__(
        self,
        id_field: str = "@id",
        reference_fields: set[str] | None = None,
    ) -> None:
        self._id_field = id_field
        self._reference_fields = reference_fields or {"@ref", "ref", "parent"}

        self._graph: Graph | None = None
        self._node_counter = 0
        self._edge_counter = 0
        self._external_to_internal_node_id: dict[str, str] = {}
        self._pending_references: list[_PendingReference] = []

    def parse(self, payload: Any, graph_id: str) -> Graph:
        self._graph = Graph(graph_id=graph_id,
                            directed_default=True, allow_cycles=True)
        self._node_counter = 0
        self._edge_counter = 0
        self._external_to_internal_node_id = {}
        self._pending_references = []

        if isinstance(payload, dict):
            self._visit_object(payload, parent_node_id=None,
                               relation_name=None)
        elif isinstance(payload, list):
            root_node_id = self._create_generated_node("json-root")
            root_node = self._require_graph().nodes[root_node_id]
            root_node.set_attribute("kind", "root-array")
            self._visit_list(payload, root_node_id, "items")
        else:
            root_node_id = self._create_generated_node("json-root")
            root_node = self._require_graph().nodes[root_node_id]
            root_node.set_attribute("kind", "root-primitive")
            root_node.set_attribute("value", self._coerce_primitive(payload))

        self._resolve_pending_references()
        return self._require_graph()

    def _visit_object(
        self,
        obj: dict[str, Any],
        parent_node_id: str | None,
        relation_name: str | None,
    ) -> str:
        node_id = self._create_or_get_object_node(obj)

        if parent_node_id is not None and relation_name is not None:
            self._add_edge(parent_node_id, node_id, relation_name)

        current_node = self._require_graph().nodes[node_id]
        for key, value in obj.items():
            if key == self._id_field:
                continue

            if self._is_reference_field(key, value):
                self._register_reference(
                    source_node_id=node_id,
                    relation_name=key,
                    target_external_id=value,
                    index=None,
                )
                continue

            if isinstance(value, dict):
                self._visit_object(
                    value, parent_node_id=node_id, relation_name=key)
                continue

            if isinstance(value, list):
                self._visit_list(
                    value, parent_node_id=node_id, relation_name=key)
                continue

            current_node.set_attribute(key, self._coerce_primitive(value))

        return node_id

    def _visit_list(self, values: list[Any], parent_node_id: str, relation_name: str) -> None:
        for index, value in enumerate(values):
            if isinstance(value, dict):
                child_node_id = self._visit_object(
                    value, parent_node_id=None, relation_name=None)
                self._add_edge(parent_node_id, child_node_id,
                               relation_name, index=index)
                continue

            if isinstance(value, list):
                list_node_id = self._create_generated_node("json-list")
                list_node = self._require_graph().nodes[list_node_id]
                list_node.set_attribute("kind", "list")
                self._add_edge(parent_node_id, list_node_id,
                               relation_name, index=index)
                self._visit_list(
                    value, parent_node_id=list_node_id, relation_name="items")
                continue

            value_node_id = self._create_generated_node("json-value")
            value_node = self._require_graph().nodes[value_node_id]
            value_node.set_attribute("value", self._coerce_primitive(value))
            self._add_edge(parent_node_id, value_node_id,
                           relation_name, index=index)

    def _create_or_get_object_node(self, obj: dict[str, Any]) -> str:
        external_id_raw = obj.get(self._id_field)
        if external_id_raw is not None:
            external_id = str(external_id_raw)
            existing = self._external_to_internal_node_id.get(external_id)
            if existing is not None:
                return existing

            node_id = external_id
            if node_id in self._require_graph().nodes:
                raise GraphValidationError(
                    f"Duplicate node id '{node_id}' detected while parsing JSON object."
                )
            node = Node(node_id=node_id)
            node.set_attribute(self._id_field, external_id)
            self._require_graph().add_node(node)
            self._external_to_internal_node_id[external_id] = node_id
            return node_id

        return self._create_generated_node("json-object")

    def _create_generated_node(self, prefix: str) -> str:
        self._node_counter += 1
        node_id = f"{prefix}-{self._node_counter}"
        self._require_graph().add_node(Node(node_id=node_id))
        return node_id

    def _add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_name: str,
        index: int | None = None,
        reference_id: str | None = None,
    ) -> None:
        self._edge_counter += 1
        edge = Edge(
            edge_id=f"json-edge-{self._edge_counter}",
            source_id=source_id,
            target_id=target_id,
            directed=True,
        )
        edge.set_attribute("relation", relation_name)
        if index is not None:
            edge.set_attribute("index", index)
        if reference_id is not None:
            edge.set_attribute("reference", reference_id)
        self._require_graph().add_edge(edge)

    def _register_reference(
        self,
        source_node_id: str,
        relation_name: str,
        target_external_id: str,
        index: int | None,
    ) -> None:
        target_node_id = self._external_to_internal_node_id.get(
            target_external_id)
        if target_node_id is not None:
            self._add_edge(
                source_id=source_node_id,
                target_id=target_node_id,
                relation_name=relation_name,
                index=index,
                reference_id=target_external_id,
            )
            return

        self._pending_references.append(
            _PendingReference(
                source_node_id=source_node_id,
                relation_name=relation_name,
                target_external_id=target_external_id,
                index=index,
            )
        )

    def _resolve_pending_references(self) -> None:
        unresolved: list[_PendingReference] = []
        for pending in self._pending_references:
            target_node_id = self._external_to_internal_node_id.get(
                pending.target_external_id)
            if target_node_id is None:
                unresolved.append(pending)
                continue

            self._add_edge(
                source_id=pending.source_node_id,
                target_id=target_node_id,
                relation_name=pending.relation_name,
                index=pending.index,
                reference_id=pending.target_external_id,
            )

        if unresolved:
            unresolved_ids = sorted(
                {item.target_external_id for item in unresolved})
            raise JsonReferenceResolutionError(
                f"Unable to resolve JSON references for ids: {', '.join(unresolved_ids)}"
            )

    def _is_reference_field(self, key: str, value: Any) -> bool:
        return key in self._reference_fields and isinstance(value, str)

    def _coerce_primitive(self, value: PrimitiveValue | Any) -> int | float | str | date:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return value
        if isinstance(value, str):
            parsed_date = self._try_parse_date(value)
            return parsed_date if parsed_date is not None else value
        return str(value)

    def _try_parse_date(self, value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _require_graph(self) -> Graph:
        if self._graph is None:
            raise RuntimeError("Parser graph context is not initialized.")
        return self._graph
