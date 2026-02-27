from __future__ import annotations
from data_source_plugin_json.parser import JsonGraphParser
from data_source_plugin_json.errors import JsonReferenceResolutionError


import sys
import os
import unittest
import json
from datetime import date

# Ensure 'api' is in sys.path for graph_api imports
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../api')))


class JsonGraphParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = JsonGraphParser()

    def test_parse_acyclic_json_builds_nodes_edges_and_attributes(self) -> None:
        payload = {
            "@id": "root",
            "name": "Root",
            "created": "2026-02-01",
            "children": [
                {"@id": "c1", "name": "Child One", "value": 10},
                {"@id": "c2", "name": "Child Two", "value": 20},
            ],
        }

        graph = self.parser.parse(payload=payload, graph_id="g1")

        self.assertEqual(graph.graph_id, "g1")
        self.assertIn("root", graph.nodes)
        self.assertIn("c1", graph.nodes)
        self.assertIn("c2", graph.nodes)
        self.assertEqual(graph.nodes["root"].attributes["name"], "Root")
        self.assertEqual(
            graph.nodes["root"].attributes["created"], date(2026, 2, 1))
        self.assertGreaterEqual(len(graph.edges), 2)

    def test_parse_cyclic_json_resolves_parent_reference(self) -> None:
        payload = {
            "@id": "parent",
            "name": "Parent",
            "children": [
                {"@id": "child1", "name": "Child 1", "parent": "parent"},
                {"@id": "child2", "name": "Child 2", "parent": "parent"},
            ],
        }

        graph = self.parser.parse(payload=payload, graph_id="g2")
        edges_to_parent = [
            edge
            for edge in graph.edges.values()
            if edge.source_id in {"child1", "child2"} and edge.target_id == "parent"
        ]

        self.assertEqual(len(edges_to_parent), 2)

    def test_parse_fails_when_reference_cannot_be_resolved(self) -> None:
        payload = {
            "@id": "a",
            "parent": "missing-node",
        }

        with self.assertRaises(JsonReferenceResolutionError):
            self.parser.parse(payload=payload, graph_id="g3")

    def test_parse_employees_json(self):
        json_path = os.path.join(os.path.dirname(__file__), "employees.json")
        parser = JsonGraphParser(id_field="id")
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        graph = parser.parse(payload, graph_id="employees")
        # Root node (auto-generated), plus one for each employee, plus many nested nodes
        self.assertTrue(len(graph.nodes) > 10)
        self.assertTrue(len(graph.edges) > 10)
        # Check that all employee ids are present as nodes
        for eid in ["E00001", "E00002", "E00003", "E00004"]:
            self.assertIn(eid, graph.nodes)
        # Check that employee nodes have name attribute
        for eid in ["E00001", "E00002", "E00003", "E00004"]:
            self.assertIn("name", graph.nodes[eid].attributes)


if __name__ == "__main__":
    unittest.main()
