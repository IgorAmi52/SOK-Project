from __future__ import annotations

from dataclasses import dataclass, field

from .attribute import AttributeMap, AttributeValue, validate_attribute_value


@dataclass(slots=True)
class Node:
    """A single vertex in a graph, identified by a unique node_id."""

    node_id: str
    attributes: AttributeMap = field(default_factory=dict)

    def set_attribute(self, name: str, value: AttributeValue) -> None:
        """Set or overwrite an attribute on this node.

        Args:
            name: Attribute key.
            value: Attribute value (must be an allowed type).
        """
        validate_attribute_value(value)
        self.attributes[name] = value
