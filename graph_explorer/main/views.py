from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode
from uuid import uuid4

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

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
    from graph_platform.core.errors import QueryValidationError
    from graph_platform.core.workspace import Workspace
    from graph_platform.core.workspace_service import WorkspaceService

    registry = _get_registry()
    error_message = None
    graph_html = None
    tree_graph = None
    node_count = 0
    edge_count = 0
    visualizers: list[dict[str, str]] = []
    current_visualizer = request.GET.get("visualizer", "simple-visualizer")
    search_queries = [value for value in request.GET.getlist(
        "search") if value.strip()]
    filter_queries = [value for value in request.GET.getlist(
        "filter") if value.strip()]
    search_query = search_queries[-1] if search_queries else ""
    filter_query = filter_queries[-1] if filter_queries else ""

    # Get data source and file path from query params
    data_source_id = request.GET.get("data_source", "")
    file_path = request.GET.get("file_path", "")

    if not registry:
        error_message = "Platform is not installed."
        return render(request, "main/workspace.html", {
            "error_message": error_message,
            "visualizers": [],
            "current_visualizer": current_visualizer,
            "tree_graph": tree_graph,
        })

    if request.method == "POST":
        data_source_id = request.POST.get("data_source", "").strip()
        file_path = request.POST.get("file_path", "").strip()
        uploaded_source = request.FILES.get("source_file")
        if uploaded_source:
            file_path = _persist_uploaded_source_file(uploaded_source)

        if data_source_id and file_path:
            query_params: dict[str, str] = {
                "data_source": data_source_id,
                "file_path": file_path,
            }

            try:
                data_source = registry.get_data_source(data_source_id)
                for parameter in data_source.parameters:
                    if parameter.name == "file_path":
                        continue
                    value = request.POST.get(parameter.name, "").strip()
                    if value:
                        query_params[parameter.name] = value
            except KeyError:
                pass

            workspace_url = reverse("workspace")
            return redirect(f"{workspace_url}?{urlencode(query_params)}")

        error_message = "Choose a file or enter a valid file path."

    visualizers = [
        {"id": plugin.plugin_id, "name": plugin.display_name}
        for plugin in registry.list_visualizers()
    ]

    if data_source_id and file_path:
        try:
            # Load graph from data source
            data_source = registry.get_data_source(data_source_id)
            load_params: dict[str, str] = {}
            for parameter in data_source.parameters:
                value = request.GET.get(parameter.name, "").strip()
                if value:
                    load_params[parameter.name] = value
            base_graph = data_source.load_graph(load_params)
            workspace_state = Workspace(
                workspace_id=f"workspace:{data_source_id}",
                source_plugin_id=data_source_id,
                source_parameters=load_params,
                base_graph=base_graph,
                current_graph=base_graph,
            )
            workspace_service = WorkspaceService()

            for operation_name, query_text in _iter_graph_operations(request):
                try:
                    if operation_name == "search":
                        workspace_service.apply_search(
                            workspace_state, query_text)
                    elif operation_name == "filter":
                        workspace_service.apply_filter(
                            workspace_state, query_text)
                except QueryValidationError as ex:
                    error_message = str(ex)
                    break

            graph = workspace_state.current_graph

            node_count = len(graph.nodes)
            edge_count = len(graph.edges)

            # Render with selected visualizer
            visualizer = registry.get_visualizer(current_visualizer)
            selected_node = request.GET.get("selected_node")
            graph_html = visualizer.render(graph, selected_node)
            tree_graph = _build_tree_graph_payload(graph)

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
            "tree_graph": tree_graph,
        },
    )


def _iter_graph_operations(request: HttpRequest) -> list[tuple[str, str]]:
    operations: list[tuple[str, str]] = []
    for key, value in parse_qsl(request.META.get("QUERY_STRING", ""), keep_blank_values=False):
        if key not in {"search", "filter"}:
            continue
        query_text = value.strip()
        if query_text:
            operations.append((key, query_text))
    return operations


def _serialize_attribute_value(value: int | str | float | date) -> str | int | float:
    if isinstance(value, date):
        return value.isoformat()
    return value


def _build_tree_graph_payload(graph) -> dict[str, object]:
    nodes = []
    for node_id, node in graph.nodes.items():
        attributes = {
            attr_name: _serialize_attribute_value(attr_value)
            for attr_name, attr_value in node.attributes.items()
        }
        nodes.append(
            {
                "id": node_id,
                "attributes": attributes,
            }
        )

    edges = []
    for edge in graph.edges.values():
        edges.append(
            {
                "id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "directed": edge.directed,
            }
        )

    return {
        "graph_id": graph.graph_id,
        "nodes": nodes,
        "edges": edges,
    }


def _persist_uploaded_source_file(uploaded_file) -> str:
    uploads_dir = Path(gettempdir()) / "sok_project_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(uploaded_file.name).suffix[:20]
    generated_name = f"{uuid4().hex}{suffix}"
    stored_path = uploads_dir / generated_name

    with stored_path.open("wb") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return str(stored_path)
