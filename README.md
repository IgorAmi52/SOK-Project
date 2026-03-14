# SOK Project - Graph Explorer

## Team

- Igor Amidžić
- Nikola Stevanović
- Miloš Jovanović
- Miloš Damjanović
- Zoran Repić

## Project Structure

Main components:

- `api` (shared graph API)
- `platform` (core graph platform and plugin registry)
- `data_source_plugin_json`, `data_source_csv`, `data_source_yaml`
- `simple_visualizer`, `block_visualizer`
- `graph_explorer` (Django app)
- `graph_explorer_flask` (Flask entrypoint)

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

## Running Django

```powershell
$env:PYTHONPATH='api;platform;data_source_plugin_json;data_source_csv;data_source_yaml;simple_visualizer;block_visualizer'
python graph_explorer/manage.py runserver
```

Open: `http://127.0.0.1:8000/`

## Running Flask

```powershell
$env:PYTHONPATH='api;platform;data_source_plugin_json;data_source_csv;data_source_yaml;simple_visualizer;block_visualizer'
python graph_explorer_flask/app.py
```

Open: `http://127.0.0.1:5000/`

## Notes

- Graphs support directed/undirected and cyclic/acyclic modes.
- Workspace supports multiple graphs with independent filters/searches.
- CLI is available in the Workspace sidebar.
