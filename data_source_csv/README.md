# CSV Data Source Plugin

`data_source_csv` is a pluggable data-source package that implements the shared
`DataSourcePlugin` contract from `graph-api`.

It uses:
- Template Method for the parsing pipeline (`load -> read -> parse -> build -> validate`)
- Strategy for CSV representation variants

Currently implemented strategy:
- `edge_list`
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

## Adjacency List CSV Format

Required columns:
- `source`
- `targets`

Optional columns:
- `directed` (`true/false`, `yes/no`, `1/0`)
- `edge_id` (allowed only when a row has a single target)
- `source_<attr_name>` for source-node attributes
- `edge_<attr_name>` for generated edge attributes

Notes:
- `targets` must contain one or more target ids separated by `|`.
- Each source-target pair becomes one edge.
- Type inference is applied the same way as in edge-list format.

Example:

```csv
source,targets,directed,source_role,source_joined,edge_weight
n1,n2|n3,true,admin,2024-01-10,0.5
n3,n4,true,member,2024-01-15,1.25
n4,n1,false,guest,2024-01-18,2.0
```

## Matrix CSV Format

Required columns:
- `source` (row node id)
- one or more target-node columns (each column name is a target node id)

Cell semantics:
- empty, `0`, `0.0`, `false`, `no` => no edge
- `1`, `true`, `yes` => edge exists without additional attributes
- any other non-empty value => edge exists and value is stored as edge attribute `value`

Notes:
- Each non-empty matrix cell creates a directed edge from `source` row node to target column node.
- Source rows must be unique.
- Type inference is applied to `value` (int, float, date, or str).

Example:

```csv
source,n1,n2,n3
n1,0,1,0
n2,0,0,2.5
n3,yes,0,0
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
