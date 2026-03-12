from __future__ import annotations


class QueryValidationError(ValueError):
    """Raised when a user query cannot be parsed or coerced to graph attribute types."""
