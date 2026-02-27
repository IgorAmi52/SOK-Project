# CSV Data Source Plugin

`data_source_csv` is a pluggable data-source package that implements the shared
`DataSourcePlugin` contract from `graph-api`.

It uses:
- Template Method for the parsing pipeline (`load -> read -> parse -> build -> validate`)
- Strategy for CSV representation variants

Currently implemented strategy:
- `edge_list`

Extension points (planned in follow-up issues):
- `adjacency_list`
- `matrix`

## Install

From repository root:

```bash
pip install -e ./api
pip install -e ./data_source_csv
```

## Plugin Parameters

- `file_path` (required): path to CSV file.
- `format` (required): one of `edge_list`, `adjacency_list`, `matrix`.
- `delimiter` (optional): single-character delimiter, default `,`.
- `graph_id` (optional): graph id; defaults to CSV filename stem.

## Edge List CSV Format

Required columns:
- `source`
- `target`

Optional columns:
- `edge_id` (auto-generated when missing)
- `directed` (`true/false`, `yes/no`, `1/0`)
- `source_<attr_name>` for source-node attributes
- `target_<attr_name>` for target-node attributes
- `edge_<attr_name>` for edge attributes

Type inference is applied to attribute values:
- `int`, `float`, `date` (`YYYY-MM-DD`, `YYYY/MM/DD`, `DD.MM.YYYY`), otherwise `str`.

Example:

```csv
source,target,edge_id,directed,source_age,target_age,edge_weight,source_joined
n1,n2,e1,true,21,22,0.5,2024-01-10
n2,n3,e2,false,22,23,1.25,2024-02-11
```

## Usage Example

```python
from csv_data_source import CsvDataSourcePlugin

plugin = CsvDataSourcePlugin()
graph = plugin.load_graph(
    {
        "file_path": "/path/to/graph.csv",
        "format": "edge_list",
        "delimiter": ",",
    }
)
```
