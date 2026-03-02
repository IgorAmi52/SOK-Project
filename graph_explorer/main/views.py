from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

if TYPE_CHECKING:
    from graph_platform.core.plugin_registry import PluginRegistry


def _get_registry() -> "PluginRegistry | None":
    """Get the plugin registry, returns None if platform not installed."""
    try:
        from graph_platform.app import create_plugin_registry
        return create_plugin_registry()
    except ImportError:
        return None


def home(request: HttpRequest) -> HttpResponse:
    data_sources: list[dict[str, str]] = []
    visualizers: list[dict[str, str]] = []
    integration_message = "Platform package is not installed yet."

    registry = _get_registry()
    if registry:
        data_sources = [
            {"id": plugin.plugin_id, "name": plugin.display_name}
            for plugin in registry.list_data_sources()
        ]
        visualizers = [
            {"id": plugin.plugin_id, "name": plugin.display_name}
            for plugin in registry.list_visualizers()
        ]
        integration_message = "Platform registry loaded successfully."

    return render(
        request,
        "main/home.html",
        {
            "integration_message": integration_message,
            "data_sources": data_sources,
            "visualizers": visualizers,
        },
    )


def workspace(request: HttpRequest) -> HttpResponse:
    """Main workspace view for graph visualization."""
    registry = _get_registry()
    error_message = None
    graph_html = None
    node_count = 0
    edge_count = 0
    visualizers: list[dict[str, str]] = []
    current_visualizer = request.GET.get("visualizer", "simple-visualizer")
    search_query = request.GET.get("search", "")
    filter_query = request.GET.get("filter", "")

    # Get data source and file path from query params
    data_source_id = request.GET.get("data_source", "")
    file_path = request.GET.get("file_path", "")

    if not registry:
        error_message = "Platform is not installed."
        return render(request, "main/workspace.html", {
            "error_message": error_message,
            "visualizers": [],
            "current_visualizer": current_visualizer,
        })

    visualizers = [
        {"id": plugin.plugin_id, "name": plugin.display_name}
        for plugin in registry.list_visualizers()
    ]

    if data_source_id and file_path:
        try:
            # Load graph from data source
            data_source = registry.get_data_source(data_source_id)
            graph = data_source.load_graph({"file_path": file_path})

            # Apply search if provided
            if search_query:
                graph = _apply_search(graph, search_query)

            # Apply filter if provided
            if filter_query:
                graph, filter_error = _apply_filter(graph, filter_query)
                if filter_error:
                    error_message = filter_error

            node_count = len(graph.nodes)
            edge_count = len(graph.edges)

            # Render with selected visualizer
            visualizer = registry.get_visualizer(current_visualizer)
            selected_node = request.GET.get("selected_node")
            graph_html = visualizer.render(graph, selected_node)

        except KeyError as ex:
            error_message = f"Plugin not found: {ex}"
        except Exception as ex:
            error_message = f"Error loading graph: {ex}"

    return render(
        request,
        "main/workspace.html",
        {
            "graph_html": graph_html,
            "error_message": error_message,
            "node_count": node_count,
            "edge_count": edge_count,
            "visualizers": visualizers,
            "current_visualizer": current_visualizer,
            "search_query": search_query,
            "filter_query": filter_query,
        },
    )


def _apply_search(graph, query: str):
    """Filter graph nodes that contain the search query in attribute names or values."""
    from graph_api.model.graph import Graph

    query_lower = query.lower()
    matching_node_ids = set()

    for node_id, node in graph.nodes.items():
        # Check if query matches node_id
        if query_lower in node_id.lower():
            matching_node_ids.add(node_id)
            continue

        # Check if query matches any attribute name or value
        for attr_name, attr_value in node.attributes.items():
            if query_lower in attr_name.lower() or query_lower in str(attr_value).lower():
                matching_node_ids.add(node_id)
                break

    return graph.create_subgraph(matching_node_ids, f"{graph.graph_id}_search")


def _apply_filter(graph, filter_query: str) -> tuple:
    """Apply filter to graph. Returns (filtered_graph, error_message)."""
    import re
    from graph_api.model.graph import Graph

    # Parse filter: attribute operator value
    pattern = r"^\s*(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)\s*$"
    match = re.match(pattern, filter_query)

    if not match:
        return graph, "Invalid filter format. Use: attribute operator value"

    attr_name, operator, raw_value = match.groups()
    raw_value = raw_value.strip().strip('"').strip("'")

    matching_node_ids = set()

    for node_id, node in graph.nodes.items():
        if attr_name not in node.attributes:
            continue

        attr_value = node.attributes[attr_name]

        # Try to parse the filter value to match the attribute type
        try:
            if isinstance(attr_value, int):
                compare_value = int(raw_value)
            elif isinstance(attr_value, float):
                compare_value = float(raw_value)
            else:
                compare_value = raw_value
        except ValueError:
            compare_value = raw_value

        # Apply comparison
        try:
            if operator == "==" and attr_value == compare_value:
                matching_node_ids.add(node_id)
            elif operator == "!=" and attr_value != compare_value:
                matching_node_ids.add(node_id)
            elif operator == ">" and attr_value > compare_value:
                matching_node_ids.add(node_id)
            elif operator == ">=" and attr_value >= compare_value:
                matching_node_ids.add(node_id)
            elif operator == "<" and attr_value < compare_value:
                matching_node_ids.add(node_id)
            elif operator == "<=" and attr_value <= compare_value:
                matching_node_ids.add(node_id)
        except TypeError:
            # Type mismatch in comparison
            continue

    return graph.create_subgraph(matching_node_ids, f"{graph.graph_id}_filter"), None
