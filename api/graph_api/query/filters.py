from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from graph_api.model.attribute import AttributeValue


class Comparator(str, Enum):
    EQ = "=="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    NE = "!="

    def evaluate(self, left: AttributeValue, right: AttributeValue) -> bool:
        if type(left) is not type(right):
            raise TypeError(
                f"Cannot compare values of different types: {type(left).__name__} and {type(right).__name__}."
            )

        left_value = left if isinstance(left, (int, str, float)) else left.isoformat()
        right_value = right if isinstance(right, (int, str, float)) else right.isoformat()

        if self is Comparator.EQ:
            return left_value == right_value
        if self is Comparator.NE:
            return left_value != right_value
        if self is Comparator.GT:
            return bool(cast(Any, left_value) > cast(Any, right_value))
        if self is Comparator.GTE:
            return bool(cast(Any, left_value) >= cast(Any, right_value))
        if self is Comparator.LT:
            return bool(cast(Any, left_value) < cast(Any, right_value))
        if self is Comparator.LTE:
            return bool(cast(Any, left_value) <= cast(Any, right_value))
        raise ValueError(f"Unsupported comparator: {self}")


@dataclass(slots=True, frozen=True)
class FilterCondition:
    attribute_name: str
    comparator: Comparator
    value: AttributeValue
