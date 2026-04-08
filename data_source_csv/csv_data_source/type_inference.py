from __future__ import annotations

import re
from datetime import datetime

from graph_api.model.attribute import AttributeValue

_INT_PATTERN = re.compile(r"[+-]?\d+")
_FLOAT_PATTERN = re.compile(r"[+-]?(?:\d+\.\d*|\d*\.\d+)")
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y")


def infer_attribute_value(raw: str) -> AttributeValue:
    """Infer a typed AttributeValue from a raw CSV cell string.

    Attempts int, float, and date conversions in order; falls back to str.

    Args:
        raw: The raw cell text.

    Returns:
        The inferred int, float, date, or original string value.
    """
    value = raw.strip()
    if value == "":
        return ""

    if _INT_PATTERN.fullmatch(value):
        return int(value)

    if _FLOAT_PATTERN.fullmatch(value):
        return float(value)

    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return value
