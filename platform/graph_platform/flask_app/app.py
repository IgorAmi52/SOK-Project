from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING
from uuid import uuid4

from flask import Flask, jsonify, redirect, render_template, request, url_for

if TYPE_CHECKING:
    from graph_platform.core.cli import CliCommandExecutor
    from graph_platform.core.plugin_registry import PluginRegistry
    from graph_platform.core.workspace import WorkspaceManager
    from graph_platform.core.workspace_service import WorkspaceService

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = BASE_DIR.parent / "django_app" / "static"

for resolved in (
    PROJECT_ROOT,
    PROJECT_ROOT / "platform",
    PROJECT_ROOT / "api",
    PROJECT_ROOT / "data_source_csv",
):
    if resolved.exists() and str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)

_WORKSPACE_MANAGER: WorkspaceManager | None = None
_WORKSPACE_SERVICE: WorkspaceService | None = None
_CLI_EXECUTOR: CliCommandExecutor | None = None
_WORKSPACE_META: dict[str, dict[str, object]] = {}
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


def _get_cli_executor() -> CliCommandExecutor | None:
    global _CLI_EXECUTOR
    if _CLI_EXECUTOR is not None:
        return _CLI_EXECUTOR

    try:
        from graph_platform.core.cli import CliCommandExecutor
    except ImportError:
        return None

    _CLI_EXECUTOR = CliCommandExecutor()
    return _CLI_EXECUTOR


@app.route("/")
def home() -> str:
    data_sources: list[dict[str, object]] = []
    visualizers: list[dict[str, str]] = []
    workspace_items: list[dict[str, object]] = []
    integration_message = "Platform package is not installed yet."

    registry = _get_registry()
    workspace_manager = _get_workspace_manager()

    if registry:
        from graph_platform.app import describe_data_sources, describe_visualizers

        data_sources = describe_data_sources(registry)
        visualizers = describe_visualizers(registry)
        integration_message = "Platform registry loaded successfully."

    if workspace_manager is not None:
        _cleanup_workspace_order(workspace_manager)
        workspace_items = _build_workspace_items(workspace_manager, active_workspace_id="")

    return render_template(
        "platform_flask/home.html",
        integration_message=integration_message,
        data_sources=data_sources,
        visualizers=visualizers,
        workspace_items=workspace_items,
    )


@app.route("/workspace/", methods=["GET", "POST"])
def workspace() -> str:
    from graph_platform.core.errors import QueryValidationError

    registry = _get_registry()
    workspace_manager = _get_workspace_manager()
    workspace_service = _get_workspace_service()
    cli_executor = _get_cli_executor()

    error_message: str | None = None
    graph_html = None
    tree_graph = None
    node_count = 0
    edge_count = 0
    visualizers: list[dict[str, str]] = []
    current_visualizer = "simple-visualizer"
    search_query = ""
    filter_query = ""
    cli_history: list[str] = []
    cli_output: list[str] = []
    cli_entries: list[dict[str, str]] = []
    active_workspace_id = ""
    active_workspace_name = ""

    if not registry or workspace_manager is None or workspace_service is None:
        return render_template(
            "platform_flask/workspace.html",
            error_message="Platform is not installed.",
            visualizers=[],
            current_visualizer=current_visualizer,
            tree_graph=tree_graph,
            workspace_items=[],
            active_workspace_id=active_workspace_id,
            active_workspace_name=active_workspace_name,
            search_query=search_query,
            filter_query=filter_query,
            cli_history=cli_history,
            cli_output=cli_output,
            cli_entries=cli_entries,
        )

    from graph_platform.app import describe_visualizers

    visualizers = describe_visualizers(registry)

    _cleanup_workspace_order(workspace_manager)

    if request.method == "POST":
        action = request.form.get("action", "create_workspace").strip()
        posted_workspace_id = request.form.get("workspace_id", "").strip()
        active_workspace_id = _resolve_active_workspace_id(posted_workspace_id, workspace_manager)

        if action == "create_workspace":
            created_id, error_message = _create_workspace_from_params(
                registry=registry,
                workspace_manager=workspace_manager,
                parameter_values=request.form,
                uploaded_source=request.files.get("source_file"),
            )
            if created_id:
                return _redirect_to_workspace(created_id)

        elif action == "switch_workspace":
            target_workspace_id = request.form.get("target_workspace_id", "").strip()
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
                selected_visualizer = request.form.get("visualizer", "").strip()
                if selected_visualizer:
                    _ensure_workspace_meta(active_workspace_id)["visualizer_id"] = selected_visualizer
            return _redirect_to_workspace(active_workspace_id)

        elif action == "search":
            query = request.form.get("search_query", "").strip()
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
            query = request.form.get("filter_query", "").strip()
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

        elif action == "execute_cli":
            from graph_platform.core.cli import CliCommandError

            command_text = request.form.get("cli_command", "").strip()
            active_workspace_id = _resolve_active_workspace_id(active_workspace_id, workspace_manager)
            if cli_executor is None:
                error_message = "CLI is not available."
            elif not active_workspace_id:
                error_message = "Create a workspace before running CLI commands."
            elif not command_text:
                error_message = "CLI command cannot be empty."
            else:
                workspace_state = workspace_manager.get(active_workspace_id)
                metadata = _ensure_workspace_meta(active_workspace_id)
                try:
                    execution_result = cli_executor.execute(workspace_state, command_text)
                    _append_cli_entry(
                        metadata,
                        command=command_text,
                        output=execution_result.message,
                    )

                    if execution_result.operation == "search" and execution_result.query is not None:
                        metadata["search_query"] = execution_result.query
                    elif execution_result.operation == "filter" and execution_result.query is not None:
                        metadata["filter_query"] = execution_result.query
                    elif execution_result.operation == "clear":
                        metadata["search_query"] = ""
                        metadata["filter_query"] = ""
                except CliCommandError as exc:
                    _append_cli_entry(
                        metadata,
                        command=command_text,
                        output=f"ERROR: {exc}",
                    )
                    error_message = str(exc)
            return _redirect_to_workspace(active_workspace_id)

        else:
            error_message = f"Unsupported action '{action}'."

    if request.method == "GET":
        requested_workspace_id = request.args.get("workspace_id", "").strip()
        active_workspace_id = _resolve_active_workspace_id(requested_workspace_id, workspace_manager)

        if not active_workspace_id:
            data_source_id = request.args.get("data_source", "").strip()
            file_path = request.args.get("file_path", "").strip()
            if data_source_id and file_path:
                created_id, error_message = _create_workspace_from_params(
                    registry=registry,
                    workspace_manager=workspace_manager,
                    parameter_values=request.args,
                    uploaded_source=None,
                )
                if created_id:
                    return _redirect_to_workspace(created_id)

    workspace_items = _build_workspace_items(workspace_manager, active_workspace_id)

    if active_workspace_id and workspace_manager.has(active_workspace_id):
        workspace_state = workspace_manager.get(active_workspace_id)
        metadata = _ensure_workspace_meta(active_workspace_id)
        active_workspace_name = str(metadata.get("name", workspace_state.workspace_id))
        current_visualizer = str(metadata.get("visualizer_id", "simple-visualizer"))
        search_query = str(metadata.get("search_query", ""))
        filter_query = str(metadata.get("filter_query", ""))
        cli_history = list(metadata.get("cli_history", []))
        cli_output = list(metadata.get("cli_output", []))
        cli_entries = [
            {"command": command, "output": output}
            for command, output in zip(cli_history, cli_output)
        ]

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

    return render_template(
        "platform_flask/workspace.html",
        graph_html=graph_html,
        error_message=error_message,
        node_count=node_count,
        edge_count=edge_count,
        visualizers=visualizers,
        current_visualizer=current_visualizer,
        search_query=search_query,
        filter_query=filter_query,
        tree_graph=tree_graph,
        workspace_items=workspace_items,
        active_workspace_id=active_workspace_id,
        active_workspace_name=active_workspace_name,
        cli_history=cli_history,
        cli_output=cli_output,
        cli_entries=cli_entries,
    )


@app.route("/api/workspace/", methods=["GET", "POST"])
def api_workspace():
    registry = _get_registry()
    workspace_manager = _get_workspace_manager()

    if not registry or workspace_manager is None:
        return jsonify({"error": "Platform is not installed."}), 500

    if request.method == "GET":
        _cleanup_workspace_order(workspace_manager)
        return jsonify({"workspaces": _build_workspace_items(workspace_manager, active_workspace_id="")})

    try:
        payload = _parse_request_payload(request)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    created_id, error_message = _create_workspace_from_params(
        registry=registry,
        workspace_manager=workspace_manager,
        parameter_values=payload,
        uploaded_source=request.files.get("source_file"),
    )
    if error_message:
        return jsonify({"error": error_message}), 400
    if not created_id:
        return jsonify({"error": "Failed to create workspace."}), 400

    workspace_state = workspace_manager.get(created_id)
    metadata = _ensure_workspace_meta(created_id)
    return jsonify(
        {
            "workspace_id": created_id,
            "workspace": _serialize_workspace_detail(workspace_state, metadata),
        }
    )


@app.route("/api/workspace/<workspace_id>/", methods=["GET", "PUT", "PATCH", "DELETE", "POST"])
def api_workspace_detail(workspace_id: str):
    workspace_manager = _get_workspace_manager()
    workspace_service = _get_workspace_service()

    if workspace_manager is None or workspace_service is None:
        return jsonify({"error": "Platform is not installed."}), 500

    if not workspace_manager.has(workspace_id):
        return jsonify({"error": f"Workspace '{workspace_id}' not found."}), 404

    workspace_state = workspace_manager.get(workspace_id)
    metadata = _ensure_workspace_meta(workspace_id)

    if request.method == "GET":
        return jsonify({"workspace": _serialize_workspace_detail(workspace_state, metadata)})

    if request.method in {"PUT", "PATCH"}:
        try:
            payload = _parse_request_payload(request)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        if "name" in payload:
            metadata["name"] = str(payload.get("name") or "").strip() or metadata.get("name", workspace_id)
        if "visualizer_id" in payload:
            metadata["visualizer_id"] = str(payload.get("visualizer_id") or metadata.get("visualizer_id"))
        return jsonify({"workspace": _serialize_workspace_detail(workspace_state, metadata)})

    if request.method == "DELETE":
        workspace_manager.remove(workspace_id)
        _WORKSPACE_META.pop(workspace_id, None)
        _WORKSPACE_ORDER[:] = [item for item in _WORKSPACE_ORDER if item != workspace_id]
        return jsonify({"deleted": True})

    try:
        payload = _parse_request_payload(request)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    action = str(payload.get("action", "")).strip().lower()
    if action != "reset":
        return jsonify({"error": "Unsupported action."}), 400

    workspace_service.reset_graph(workspace_state)
    metadata["search_query"] = ""
    metadata["filter_query"] = ""
    return jsonify({"workspace": _serialize_workspace_detail(workspace_state, metadata)})


@app.route("/api/cli/", methods=["POST"])
def api_cli():
    from graph_platform.core.cli import CliCommandError

    workspace_manager = _get_workspace_manager()
    cli_executor = _get_cli_executor()

    if workspace_manager is None or cli_executor is None:
        return jsonify({"error": "Platform is not installed."}), 500

    try:
        payload = _parse_request_payload(request)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    workspace_id = str(payload.get("workspace_id", "")).strip()
    command_text = str(payload.get("command", "")).strip()
    if not workspace_id:
        return jsonify({"error": "Missing required field: workspace_id."}), 400
    if not command_text:
        return jsonify({"error": "Missing required field: command."}), 400
    if not workspace_manager.has(workspace_id):
        return jsonify({"error": f"Workspace '{workspace_id}' not found."}), 404

    workspace_state = workspace_manager.get(workspace_id)
    metadata = _ensure_workspace_meta(workspace_id)

    try:
        execution_result = cli_executor.execute(workspace_state, command_text)
        _append_cli_entry(metadata, command=command_text, output=execution_result.message)

        if execution_result.operation == "search" and execution_result.query is not None:
            metadata["search_query"] = execution_result.query
        elif execution_result.operation == "filter" and execution_result.query is not None:
            metadata["filter_query"] = execution_result.query
        elif execution_result.operation == "clear":
            metadata["search_query"] = ""
            metadata["filter_query"] = ""

        return jsonify(
            {
                "message": execution_result.message,
                "operation": execution_result.operation,
                "query": execution_result.query,
                "workspace_id": workspace_id,
            }
        )
    except CliCommandError as exc:
        _append_cli_entry(metadata, command=command_text, output=f"ERROR: {exc}")
        return jsonify({"error": str(exc)}), 400


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
    current_graph = base_graph.create_subgraph(
        set(base_graph.nodes.keys()),
        subgraph_id=base_graph.graph_id,
    )
    workspace_state = Workspace(
        workspace_id=workspace_id,
        source_plugin_id=data_source_id,
        source_parameters=load_params,
        base_graph=base_graph,
        current_graph=current_graph,
    )
    workspace_manager.add(workspace_state)
    _WORKSPACE_ORDER.append(workspace_id)

    workspace_name = parameter_values.get("workspace_name", "").strip()
    if not workspace_name:
        workspace_name = _build_default_workspace_name(data_source.display_name)

    _WORKSPACE_META[workspace_id] = {
        "name": workspace_name,
        "visualizer_id": "simple-visualizer",
        "search_query": "",
        "filter_query": "",
        "cli_history": [],
        "cli_output": [],
    }
    return workspace_id, None


def _build_default_workspace_name(base_name: str) -> str:
    normalized_base = base_name.strip() or "Workspace"
    existing_names = {
        str(meta.get("name", "")).strip().lower()
        for meta in _WORKSPACE_META.values()
    }
    if normalized_base.lower() not in existing_names:
        return normalized_base

    suffix = 2
    while True:
        candidate = f"{normalized_base} {suffix}"
        if candidate.lower() not in existing_names:
            return candidate
        suffix += 1


def _cleanup_workspace_order(workspace_manager: WorkspaceManager) -> None:
    _WORKSPACE_ORDER[:] = [
        workspace_id for workspace_id in _WORKSPACE_ORDER if workspace_manager.has(workspace_id)
    ]


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


def _ensure_workspace_meta(workspace_id: str) -> dict[str, object]:
    metadata = _WORKSPACE_META.get(workspace_id)
    if metadata is None:
        metadata = {
            "name": workspace_id,
            "visualizer_id": "simple-visualizer",
            "search_query": "",
            "filter_query": "",
            "cli_history": [],
            "cli_output": [],
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
                "name": str(metadata.get("name", workspace_id)),
                "is_active": workspace_id == active_workspace_id,
                "node_count": len(workspace_state.current_graph.nodes),
                "edge_count": len(workspace_state.current_graph.edges),
            }
        )
    return items


def _append_cli_entry(metadata: dict[str, object], command: str, output: str) -> None:
    history = list(metadata.get("cli_history", []))
    messages = list(metadata.get("cli_output", []))
    history.append(command)
    messages.append(output)

    max_entries = 100
    if len(history) > max_entries:
        history = history[-max_entries:]
    if len(messages) > max_entries:
        messages = messages[-max_entries:]

    metadata["cli_history"] = history
    metadata["cli_output"] = messages


def _redirect_to_workspace(workspace_id: str):
    if workspace_id:
        return redirect(url_for("workspace", workspace_id=workspace_id))
    return redirect(url_for("workspace"))


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


def _parse_request_payload(raw_request) -> dict[str, str]:
    if raw_request.is_json:
        payload = raw_request.get_json(silent=True)
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object.")
        return {str(key): "" if value is None else str(value) for key, value in payload.items()}
    if raw_request.form:
        return {str(key): str(value) for key, value in raw_request.form.items()}
    return {}


def _serialize_workspace_detail(workspace_state, metadata: dict[str, object]) -> dict[str, object]:
    graph = workspace_state.current_graph
    return {
        "id": workspace_state.workspace_id,
        "name": str(metadata.get("name", workspace_state.workspace_id)),
        "source_plugin_id": workspace_state.source_plugin_id,
        "source_parameters": dict(workspace_state.source_parameters),
        "visualizer_id": str(metadata.get("visualizer_id", "simple-visualizer")),
        "search_query": str(metadata.get("search_query", "")),
        "filter_query": str(metadata.get("filter_query", "")),
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "graph_id": graph.graph_id,
    }


def _persist_uploaded_source_file(uploaded_file) -> str:
    uploads_dir = Path(gettempdir()) / "sok_project_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(uploaded_file.filename or "").suffix[:20]
    generated_name = f"{uuid4().hex}{suffix}"
    stored_path = uploads_dir / generated_name

    uploaded_file.save(stored_path)

    return str(stored_path)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes"))
