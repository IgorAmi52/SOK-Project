from __future__ import annotations

from datetime import date

AttributeValue = int | str | float | date
AttributeMap = dict[str, AttributeValue]


ALLOWED_ATTRIBUTE_TYPES = (int, str, float, date)


def validate_attribute_value(value: object) -> None:
    if not isinstance(value, ALLOWED_ATTRIBUTE_TYPES):
        raise TypeError(
            "Unsupported attribute value type. Allowed types are int, str, float, date."
        )
