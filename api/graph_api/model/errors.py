class GraphError(Exception):
    """Base exception for all graph-related errors."""


class GraphValidationError(GraphError):
    """Raised when graph data fails validation (e.g. duplicate ids, missing nodes)."""


class GraphConstraintError(GraphError):
    """Raised when an operation would violate a graph constraint (e.g. cycles, connected nodes)."""
