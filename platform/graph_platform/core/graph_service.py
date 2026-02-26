from __future__ import annotations

from graph_api.model.graph import Graph
from graph_api.query.filters import FilterCondition
from graph_api.query.search import SearchQuery


class GraphService:
    def filter_graph(self, graph: Graph, condition: FilterCondition, subgraph_id: str) -> Graph:
        matching_node_ids: set[str] = set()
        for node in graph.nodes.values():
            attribute_value = node.attributes.get(condition.attribute_name)
            if attribute_value is None:
                continue
            if type(attribute_value) is not type(condition.value):
                continue
            if condition.comparator.evaluate(attribute_value, condition.value):
                matching_node_ids.add(node.node_id)
        return graph.create_subgraph(matching_node_ids, subgraph_id=subgraph_id)

    def search_graph(self, graph: Graph, query: SearchQuery, subgraph_id: str) -> Graph:
        needle = query.normalized()
        matching_node_ids: set[str] = set()
        for node in graph.nodes.values():
            for attr_name, attr_value in node.attributes.items():
                if needle in attr_name.lower() or needle in str(attr_value).lower():
                    matching_node_ids.add(node.node_id)
                    break
        return graph.create_subgraph(matching_node_ids, subgraph_id=subgraph_id)
