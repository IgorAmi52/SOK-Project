from __future__ import annotations

from datetime import date

AttributeValue = int | str | float | date
AttributeMap = dict[str, AttributeValue]


ALLOWED_ATTRIBUTE_TYPES = (int, str, float, date)


def validate_attribute_value(value: object) -> None:
    """Raise TypeError if *value* is not an allowed attribute type.

    Args:
        value: The value to validate.

    Raises:
        TypeError: If the value's type is not in ALLOWED_ATTRIBUTE_TYPES.
    """
    if not isinstance(value, ALLOWED_ATTRIBUTE_TYPES):
        raise TypeError(
            "Unsupported attribute value type. Allowed types are int, str, float, date."
        )
