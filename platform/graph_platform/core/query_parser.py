from __future__ import annotations

from collections.abc import Container
from datetime import date

from graph_api.model.attribute import AttributeValue
from graph_api.model.graph import Graph
from graph_api.query.filters import Comparator, FilterCondition
from graph_api.query.search import SearchQuery

from .errors import QueryValidationError

_COMPARATORS_IN_PARSE_ORDER = [
    Comparator.GTE,
    Comparator.LTE,
    Comparator.EQ,
    Comparator.NE,
    Comparator.GT,
    Comparator.LT,
]


def parse_search_query(text: str) -> SearchQuery:
    normalized = text.strip()
    if not normalized:
        raise QueryValidationError("Search query cannot be empty.")
    return SearchQuery(text=normalized)


def parse_filter_condition(text: str, graph: Graph) -> FilterCondition:
    attribute_name, comparator, raw_value = _split_filter_parts(text)
    value = _coerce_filter_value(attribute_name, raw_value, graph)

    return FilterCondition(
        attribute_name=attribute_name,
        comparator=comparator,
        value=value,
    )


def _split_filter_parts(text: str) -> tuple[str, Comparator, str]:
    for comparator in _COMPARATORS_IN_PARSE_ORDER:
        if comparator.value not in text:
            continue

        attribute_name, raw_value = text.split(comparator.value, maxsplit=1)
        attribute_name = attribute_name.strip()
        raw_value = raw_value.strip()

        if not attribute_name or not raw_value:
            break

        return attribute_name, comparator, raw_value

    raise QueryValidationError(
        "Invalid filter format. Expected '<attribute> <comparator> <value>'."
    )


def _coerce_filter_value(attribute_name: str, raw_value: str, graph: Graph) -> AttributeValue:
    candidate_types = {
        type(node.attributes[attribute_name])
        for node in graph.nodes.values()
        if attribute_name in node.attributes
    }

    if not candidate_types:
        return raw_value

    if len(candidate_types) == 1:
        target_type = next(iter(candidate_types))
        return _parse_value_as_type(attribute_name, raw_value, target_type)

    parsed_errors: list[str] = []
    for target_type in _candidate_type_order(candidate_types):
        try:
            return _parse_value_as_type(attribute_name, raw_value, target_type)
        except QueryValidationError as exc:
            parsed_errors.append(str(exc))

    available_types = ", ".join(
        sorted(candidate_type.__name__ for candidate_type in candidate_types))
    raise QueryValidationError(
        f"Filter value '{raw_value}' does not match attribute '{attribute_name}' types: {available_types}."
    )


def _candidate_type_order(candidate_types: Container[type[object]]) -> list[type[object]]:
    ordered = [int, float, date, str]
    return [candidate_type for candidate_type in ordered if candidate_type in candidate_types]


def _parse_value_as_type(
    attribute_name: str,
    raw_value: str,
    target_type: type[object],
) -> AttributeValue:
    try:
        if target_type is str:
            return raw_value
        if target_type is int:
            return int(raw_value)
        if target_type is float:
            return float(raw_value)
        if target_type is date:
            return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise QueryValidationError(
            f"Filter value '{raw_value}' is not a valid {target_type.__name__} for attribute '{attribute_name}'."
        ) from exc

    raise QueryValidationError(
        f"Attribute '{attribute_name}' uses unsupported filter type '{target_type.__name__}'."
    )
