# Graph Explorer Flask App

Flask web integration for the graph platform and plugins.

## Run

From repository root:

```bash
pip install -r requirements.txt
pip install --no-build-isolation ./api ./platform ./data_source_plugin_json ./data_source_csv ./simple_visualizer
python graph_explorer_flask/app.py
```

Open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/workspace/`
