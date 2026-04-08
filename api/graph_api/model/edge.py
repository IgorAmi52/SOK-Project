from __future__ import annotations

from dataclasses import dataclass, field

from .attribute import AttributeMap, AttributeValue, validate_attribute_value


@dataclass(slots=True)
class Edge:
    """A connection between two nodes, optionally directed."""

    edge_id: str
    source_id: str
    target_id: str
    directed: bool = True
    attributes: AttributeMap = field(default_factory=dict)

    def set_attribute(self, name: str, value: AttributeValue) -> None:
        """Set or overwrite an attribute on this edge.

        Args:
            name: Attribute key.
            value: Attribute value (must be an allowed type).
        """
        validate_attribute_value(value)
        self.attributes[name] = value
