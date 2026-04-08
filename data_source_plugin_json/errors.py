class JsonDataSourceError(Exception):
    """Base exception for all JSON data-source errors."""


class JsonInputError(JsonDataSourceError):
    """Raised when the JSON input file is missing, unreadable, or malformed."""


class JsonReferenceResolutionError(JsonDataSourceError):
    """Raised when one or more JSON object references cannot be resolved."""
