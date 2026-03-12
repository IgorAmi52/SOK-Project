from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING
from uuid import uuid4

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

if TYPE_CHECKING:
    from graph_platform.core.plugin_registry import PluginRegistry
    from graph_platform.core.workspace import Workspace, WorkspaceManager
    from graph_platform.core.workspace_service import WorkspaceService


_WORKSPACE_MANAGER: WorkspaceManager | None = None
_WORKSPACE_SERVICE: WorkspaceService | None = None
_WORKSPACE_META: dict[str, dict[str, str]] = {}
_WORKSPACE_ORDER: list[str] = []


def _get_registry() -> PluginRegistry | None:
    try:
        from graph_platform.app import create_plugin_registry

        return create_plugin_registry()
    except ImportError:
        return None


def _get_workspace_manager() -> WorkspaceManager | None:
    global _WORKSPACE_MANAGER
    if _WORKSPACE_MANAGER is not None:
        return _WORKSPACE_MANAGER

    try:
        from graph_platform.core.workspace import WorkspaceManager
    except ImportError:
        return None

    _WORKSPACE_MANAGER = WorkspaceManager()
    return _WORKSPACE_MANAGER


def _get_workspace_service() -> WorkspaceService | None:
    global _WORKSPACE_SERVICE
    if _WORKSPACE_SERVICE is not None:
        return _WORKSPACE_SERVICE

    try:
        from graph_platform.core.workspace_service import WorkspaceService
    except ImportError:
        return None

    _WORKSPACE_SERVICE = WorkspaceService()
    return _WORKSPACE_SERVICE


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
    from graph_platform.core.errors import QueryValidationError
    from graph_platform.core.workspace import Workspace

    registry = _get_registry()
    workspace_manager = _get_workspace_manager()
    workspace_service = _get_workspace_service()

    error_message: str | None = None
    graph_html = None
    tree_graph = None
    node_count = 0
    edge_count = 0
    visualizers: list[dict[str, str]] = []
    current_visualizer = "simple-visualizer"
    search_query = ""
    filter_query = ""
    active_workspace_id = ""
    active_workspace_name = ""

    if not registry or workspace_manager is None or workspace_service is None:
        return render(
            request,
            "main/workspace.html",
            {
                "error_message": "Platform is not installed.",
                "visualizers": [],
                "current_visualizer": current_visualizer,
                "tree_graph": tree_graph,
                "workspace_items": [],
                "active_workspace_id": active_workspace_id,
                "active_workspace_name": active_workspace_name,
                "search_query": search_query,
                "filter_query": filter_query,
            },
        )

    visualizers = [
        {"id": plugin.plugin_id, "name": plugin.display_name}
        for plugin in registry.list_visualizers()
    ]

    _cleanup_workspace_order(workspace_manager)

    if request.method == "POST":
        action = request.POST.get("action", "create_workspace").strip()
        posted_workspace_id = request.POST.get("workspace_id", "").strip()
        active_workspace_id = _resolve_active_workspace_id(posted_workspace_id, workspace_manager)

        if action == "create_workspace":
            created_id, error_message = _create_workspace_from_params(
                registry=registry,
                workspace_manager=workspace_manager,
                parameter_values=request.POST,
                uploaded_source=request.FILES.get("source_file"),
            )
            if created_id:
                return _redirect_to_workspace(created_id)

        elif action == "switch_workspace":
            target_workspace_id = request.POST.get("target_workspace_id", "").strip()
            target_workspace_id = _resolve_active_workspace_id(target_workspace_id, workspace_manager)
            return _redirect_to_workspace(target_workspace_id)

        elif action == "delete_workspace":
            target_workspace_id = active_workspace_id
            if target_workspace_id and workspace_manager.has(target_workspace_id):
                workspace_manager.remove(target_workspace_id)
                _WORKSPACE_META.pop(target_workspace_id, None)
                _WORKSPACE_ORDER[:] = [item for item in _WORKSPACE_ORDER if item != target_workspace_id]
            next_workspace_id = _resolve_active_workspace_id("", workspace_manager)
            return _redirect_to_workspace(next_workspace_id)

        elif action == "set_visualizer":
            if active_workspace_id and workspace_manager.has(active_workspace_id):
                selected_visualizer = request.POST.get("visualizer", "").strip()
                if selected_visualizer:
                    _ensure_workspace_meta(active_workspace_id)["visualizer_id"] = selected_visualizer
            return _redirect_to_workspace(active_workspace_id)

        elif action == "search":
            query = request.POST.get("search_query", "").strip()
            active_workspace_id = _resolve_active_workspace_id(active_workspace_id, workspace_manager)
            if not active_workspace_id:
                error_message = "Create a workspace before running search."
            elif not query:
                error_message = "Search query cannot be empty."
            else:
                workspace_state = workspace_manager.get(active_workspace_id)
                try:
                    workspace_service.apply_search(workspace_state, query)
                    _ensure_workspace_meta(active_workspace_id)["search_query"] = query
                except QueryValidationError as exc:
                    error_message = str(exc)
            if not error_message:
                return _redirect_to_workspace(active_workspace_id)

        elif action == "filter":
            query = request.POST.get("filter_query", "").strip()
            active_workspace_id = _resolve_active_workspace_id(active_workspace_id, workspace_manager)
            if not active_workspace_id:
                error_message = "Create a workspace before running filter."
            elif not query:
                error_message = "Filter query cannot be empty."
            else:
                workspace_state = workspace_manager.get(active_workspace_id)
                try:
                    workspace_service.apply_filter(workspace_state, query)
                    _ensure_workspace_meta(active_workspace_id)["filter_query"] = query
                except QueryValidationError as exc:
                    error_message = str(exc)
            if not error_message:
                return _redirect_to_workspace(active_workspace_id)

        elif action == "reset_workspace":
            active_workspace_id = _resolve_active_workspace_id(active_workspace_id, workspace_manager)
            if active_workspace_id:
                workspace_state = workspace_manager.get(active_workspace_id)
                workspace_service.reset_graph(workspace_state)
                metadata = _ensure_workspace_meta(active_workspace_id)
                metadata["search_query"] = ""
                metadata["filter_query"] = ""
            return _redirect_to_workspace(active_workspace_id)

        else:
            error_message = f"Unsupported action '{action}'."

    if request.method == "GET":
        requested_workspace_id = request.GET.get("workspace_id", "").strip()
        active_workspace_id = _resolve_active_workspace_id(requested_workspace_id, workspace_manager)

        if not active_workspace_id:
            data_source_id = request.GET.get("data_source", "").strip()
            file_path = request.GET.get("file_path", "").strip()
            if data_source_id and file_path:
                created_id, error_message = _create_workspace_from_params(
                    registry=registry,
                    workspace_manager=workspace_manager,
                    parameter_values=request.GET,
                    uploaded_source=None,
                )
                if created_id:
                    return _redirect_to_workspace(created_id)

    workspace_items = _build_workspace_items(workspace_manager, active_workspace_id)

    if active_workspace_id and workspace_manager.has(active_workspace_id):
        workspace_state = workspace_manager.get(active_workspace_id)
        metadata = _ensure_workspace_meta(active_workspace_id)
        active_workspace_name = metadata.get("name", workspace_state.workspace_id)
        current_visualizer = metadata.get("visualizer_id", "simple-visualizer")
        search_query = metadata.get("search_query", "")
        filter_query = metadata.get("filter_query", "")

        graph = workspace_state.current_graph
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)

        try:
            visualizer = registry.get_visualizer(current_visualizer)
        except KeyError:
            if visualizers:
                current_visualizer = visualizers[0]["id"]
                metadata["visualizer_id"] = current_visualizer
                visualizer = registry.get_visualizer(current_visualizer)
            else:
                visualizer = None

        if visualizer is not None:
            graph_html = visualizer.render(graph, selected_node_id=None)
        tree_graph = _build_tree_graph_payload(graph)

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
            "workspace_items": workspace_items,
            "active_workspace_id": active_workspace_id,
            "active_workspace_name": active_workspace_name,
        },
    )


def _create_workspace_from_params(
    registry: PluginRegistry,
    workspace_manager: WorkspaceManager,
    parameter_values,
    uploaded_source,
) -> tuple[str | None, str | None]:
    from graph_platform.core.workspace import Workspace

    data_source_id = parameter_values.get("data_source", "").strip()
    if not data_source_id:
        return None, "Select a data source plugin."

    file_path = parameter_values.get("file_path", "").strip()
    if uploaded_source:
        file_path = _persist_uploaded_source_file(uploaded_source)
    if not file_path:
        return None, "Choose a file or enter a valid file path."

    try:
        data_source = registry.get_data_source(data_source_id)
    except KeyError:
        return None, f"Plugin not found: {data_source_id}"

    load_params: dict[str, str] = {}
    for plugin_parameter in data_source.parameters:
        if plugin_parameter.name == "file_path":
            load_params["file_path"] = file_path
            continue
        value = parameter_values.get(plugin_parameter.name, "").strip()
        if value:
            load_params[plugin_parameter.name] = value

    try:
        base_graph = data_source.load_graph(load_params)
    except Exception as exc:
        return None, f"Error loading graph: {exc}"

    workspace_id = f"workspace-{uuid4().hex[:8]}"
    workspace_state = Workspace(
        workspace_id=workspace_id,
        source_plugin_id=data_source_id,
        source_parameters=load_params,
        base_graph=base_graph,
        current_graph=base_graph,
    )
    workspace_manager.add(workspace_state)
    _WORKSPACE_ORDER.append(workspace_id)

    workspace_name = parameter_values.get("workspace_name", "").strip()
    if not workspace_name:
        workspace_name = f"{data_source.display_name} ({base_graph.graph_id})"

    _WORKSPACE_META[workspace_id] = {
        "name": workspace_name,
        "visualizer_id": "simple-visualizer",
        "search_query": "",
        "filter_query": "",
    }
    return workspace_id, None


def _cleanup_workspace_order(workspace_manager: WorkspaceManager) -> None:
    _WORKSPACE_ORDER[:] = [workspace_id for workspace_id in _WORKSPACE_ORDER if workspace_manager.has(workspace_id)]


def _resolve_active_workspace_id(
    requested_workspace_id: str,
    workspace_manager: WorkspaceManager,
) -> str:
    _cleanup_workspace_order(workspace_manager)

    if requested_workspace_id and workspace_manager.has(requested_workspace_id):
        return requested_workspace_id

    if _WORKSPACE_ORDER:
        return _WORKSPACE_ORDER[0]

    return ""


def _ensure_workspace_meta(workspace_id: str) -> dict[str, str]:
    metadata = _WORKSPACE_META.get(workspace_id)
    if metadata is None:
        metadata = {
            "name": workspace_id,
            "visualizer_id": "simple-visualizer",
            "search_query": "",
            "filter_query": "",
        }
        _WORKSPACE_META[workspace_id] = metadata
    return metadata


def _build_workspace_items(
    workspace_manager: WorkspaceManager,
    active_workspace_id: str,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for workspace_id in _WORKSPACE_ORDER:
        if not workspace_manager.has(workspace_id):
            continue
        workspace_state = workspace_manager.get(workspace_id)
        metadata = _ensure_workspace_meta(workspace_id)
        items.append(
            {
                "id": workspace_id,
                "name": metadata.get("name", workspace_id),
                "is_active": workspace_id == active_workspace_id,
                "node_count": len(workspace_state.current_graph.nodes),
                "edge_count": len(workspace_state.current_graph.edges),
            }
        )
    return items


def _redirect_to_workspace(workspace_id: str) -> HttpResponse:
    workspace_url = reverse("workspace")
    if workspace_id:
        return redirect(f"{workspace_url}?workspace_id={workspace_id}")
    return redirect(workspace_url)


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
        nodes.append({"id": node_id, "attributes": attributes})

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

    return {"graph_id": graph.graph_id, "nodes": nodes, "edges": edges}


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
