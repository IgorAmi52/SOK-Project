# Graph Explorer

> A plugin-based graph visualization platform built with Python, Django, and Flask.

## Overview

Graph Explorer is an extensible platform for loading, querying, and visualizing graph data from multiple file formats. It features a **plugin architecture** where data-source parsers and graph visualizers are independent, installable packages discovered at runtime — making the system open for extension without modifying core code. The platform supports directed/undirected graphs, cyclic reference resolution, multi-workspace sessions, and an interactive CLI for real-time graph manipulation.

## Architecture

The system is organized into four layers connected through well-defined contracts:

```
┌──────────────────────────────────────────────────────────┐
│                   Web Frontend (Django / Flask)          │
│              D3.js force-directed & block views          │
├──────────────────────────────────────────────────────────┤
│                     Platform Core                        │
│   PluginRegistry · WorkspaceService · CLI · GraphService │
├────────────────────────────┬─────────────────────────────┤
│   Data Source Plugins      │   Visualizer Plugins        │
│  ┌───────┐ ┌────┐ ┌──────┐   ┌────────┐ ┌─────────┐      │
│  │ JSON  │ │CSV │ │ YAML │   │ Simple │ │  Block  │      │
│  └───┬───┘ └──┬─┘ └──┬───┘   └───┬────┘ └────┬────┘      │
├──────┴────────┴──────┴───────────┴───────────┴───────────┤
│                  graph-api (Contracts + Model)           │
│     DataSourcePlugin · VisualizerPlugin · Graph · Node   │
└──────────────────────────────────────────────────────────┘
```

- **graph-api** — Shared domain model (`Graph`, `Node`, `Edge`) and abstract plugin contracts (`DataSourcePlugin`, `VisualizerPlugin`).
- **Platform Core** — Plugin registry with entry-point discovery, workspace management, query engine (filter/search), and a CLI command executor.
- **Data Source Plugins** — Parse JSON, CSV (edge-list / adjacency-list / matrix), and YAML files into the common graph model. Support cyclic references.
- **Visualizer Plugins** — Render graphs as HTML/SVG using D3.js. Simple (circle + line) and Block (card with attribute rows) views.
- **Web Apps** — Django and Flask frontends providing workspace UI, multi-tab sessions, and a REST API.

## Features

- **Plugin discovery** via Python entry points and built-in fallback loading
- **Three data-source formats**: JSON (nested + cyclic refs), CSV (three sub-formats with type inference), YAML (nested + cyclic refs)
- **Two visualization modes**: force-directed circle graph and block/card graph with attribute detail
- **Three view types**: Bird's-eye graph view, tree/hierarchy view, and detail panel
- **Search and filter engine** with automatic type coercion (int, float, date, string)
- **Multi-workspace sessions** — load multiple graphs simultaneously with independent filter/search state
- **Interactive CLI** — create, edit, delete nodes and edges; search and filter from a command line
- **Cycle detection** — graphs can enforce acyclic constraints or allow cyclic structures
- **Subgraph extraction** — filter and search produce new subgraphs preserving internal edges
- **Dual web framework support** — both Django and Flask frontends ship from the same platform package

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Django 5.x, Flask 3.x |
| Graph Model | Custom plugin-based API with `abc.ABC` contracts |
| Frontend | D3.js, HTML/CSS/JavaScript, Jinja2 templates |
| Data Formats | JSON, CSV (edge-list, adjacency-list, matrix), YAML |
| Testing | unittest, pytest |
| Packaging | setuptools with `pyproject.toml` entry-point plugins |

## Project Structure

```
api/                        Shared graph model and plugin contracts
platform/                   Core platform: registry, workspace, CLI, query engine
  graph_platform/
    app/                    Plugin discovery and catalog helpers
    core/                   Business logic (services, CLI, query parser)
    django_app/             Django views, templates, static assets
    flask_app/              Flask routes and templates
data_source_plugin_json/    JSON data-source plugin
data_source_csv/            CSV data-source plugin (edge-list, adjacency-list, matrix)
data_source_yaml/           YAML data-source plugin
simple_visualizer/          D3.js force-directed circle visualizer
block_visualizer/           D3.js block/card visualizer
graph_explorer/             Django project entry point (manage.py, settings)
graph_explorer_flask/       Flask entry point
```

## Getting Started

### Prerequisites

- Python 3.11+
- `pip` and `virtualenv` (or `venv`)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd SOK-Project

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install base dependencies
pip install -r requirements.txt

# Install all components as editable packages
pip install -e ./api
pip install -e ./platform
pip install -e ./data_source_plugin_json
pip install -e ./data_source_csv
pip install -e ./data_source_yaml
pip install -e ./simple_visualizer
pip install -e ./block_visualizer
```

### Running the Django App

```bash
export PYTHONPATH="api:platform:data_source_plugin_json:data_source_csv:data_source_yaml:simple_visualizer:block_visualizer"
python graph_explorer/manage.py runserver
```

Open: http://127.0.0.1:8000/

### Running the Flask App

```bash
export PYTHONPATH="api:platform:data_source_plugin_json:data_source_csv:data_source_yaml:simple_visualizer:block_visualizer"
python graph_explorer_flask/app.py
```

Open: http://127.0.0.1:5000/

### Running Tests

```bash
python -m pytest simple_visualizer/tests/ block_visualizer/tests/
python -m unittest discover -s platform/tests
python -m unittest discover -s data_source_csv/tests
python -m unittest discover -s data_source_plugin_json/tests
```

## Usage

1. **Select a data source** (JSON, CSV, or YAML) from the home page
2. **Upload or specify a file path** and configure format-specific parameters
3. **Explore the graph** using the bird's-eye view (force-directed layout) or tree view
4. **Switch visualizers** between Simple (circles) and Block (cards with attributes)
5. **Filter and search** using the sidebar — e.g., `age>=30` or search for `Alice`
6. **Use the CLI** for fine-grained control: `create node --id=n5 --property name=Eve`

<!-- TODO: Add a screenshot or GIF of the workspace view here -->

## Design Patterns Applied

| Pattern | Location | Purpose |
|---|---|---|
| **Strategy** | `DataSourcePlugin`, `VisualizerPlugin`, `CsvFormatStrategy` | Interchangeable algorithms for parsing and rendering |
| **Template Method** | `CsvParsingPipeline` | Fixed `load → read → parse → build → validate` skeleton with overridable steps |
| **Abstract Factory** | `create_plugin_registry()` | Discovers and instantiates plugins via entry points and built-in fallbacks |
| **Registry** | `PluginRegistry` | Central catalog for runtime plugin lookup |
| **Facade** | `WorkspaceService` | Simplified interface for filter/search/reset operations |
| **Command** | `CliCommandExecutor` | Parses text commands into graph mutations |
| **Dataclass Value Objects** | `Graph`, `Node`, `Edge`, `FilterCondition` | Immutable/slotted domain model objects |

## Plugin Development

Creating a new plugin is straightforward. Implement one of the abstract contracts from `graph-api`:

```python
from graph_api.contracts.data_source import DataSourcePlugin, PluginParameter
from graph_api.model.graph import Graph

class MyDataSource(DataSourcePlugin):
    @property
    def plugin_id(self) -> str:
        return "my-data-source"

    @property
    def display_name(self) -> str:
        return "My Data Source"

    @property
    def parameters(self) -> list[PluginParameter]:
        return [PluginParameter(name="file_path", description="Path to input file")]

    def load_graph(self, parameter_values: dict[str, str]) -> Graph:
        # Parse your data and build a Graph
        ...
```

Register the plugin as a Python entry point in your `pyproject.toml`:

```toml
[project.entry-points."graph_platform.data_source_plugins"]
my_source = "my_package.plugin:MyDataSource"
```

Install the package and the platform will discover it automatically.
