from __future__ import annotations

from dataclasses import dataclass, field

from .attribute import AttributeMap, AttributeValue, validate_attribute_value


@dataclass(slots=True)
class Edge:
    edge_id: str
    source_id: str
    target_id: str
    directed: bool = True
    attributes: AttributeMap = field(default_factory=dict)

    def set_attribute(self, name: str, value: AttributeValue) -> None:
        validate_attribute_value(value)
        self.attributes[name] = value
