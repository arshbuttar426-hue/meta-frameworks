from __future__ import annotations
from capabilities.base import (
    CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass,
)
from capabilities.registry import CapabilityRegistry

numpy_compute_decl = CapabilityDeclaration(
    name="numpy_compute",
    description="Execute NumPy array operations including linear algebra, statistics, and transformations",
    inputs=[CapabilityIO(name="operation", type="string", description="numpy operation to perform"),
            CapabilityIO(name="data", type="any"), CapabilityIO(name="kwargs", type="dict", required=False)],
    outputs=[CapabilityIO(name="result", type="any")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=False,
    category="data_science", tags=["numpy", "computation"],
)

pandas_analyze_decl = CapabilityDeclaration(
    name="pandas_analyze",
    description="Analyze tabular data using Pandas: describe, group, join, pivot",
    inputs=[CapabilityIO(name="operation", type="string"),
            CapabilityIO(name="data", type="list[dict]", description="Data as list of dicts"),
            CapabilityIO(name="kwargs", type="dict", required=False)],
    outputs=[CapabilityIO(name="result", type="any"), CapabilityIO(name="summary", type="dict")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=False,
    category="data_science", tags=["pandas", "dataframe", "analysis"],
)

polars_analyze_decl = CapabilityDeclaration(
    name="polars_analyze",
    description="Analyze tabular data using Polars DataFrame for large datasets",
    inputs=[CapabilityIO(name="operation", type="string"),
            CapabilityIO(name="data", type="list[dict]"),
            CapabilityIO(name="kwargs", type="dict", required=False)],
    outputs=[CapabilityIO(name="result", type="any"), CapabilityIO(name="summary", type="dict")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=False,
    category="data_science", tags=["polars", "dataframe", "large_data"],
)

duckdb_query_decl = CapabilityDeclaration(
    name="duckdb_query",
    description="Execute SQL queries on tabular data using DuckDB",
    inputs=[CapabilityIO(name="query", type="string", description="SQL query"),
            CapabilityIO(name="data", type="any", required=False, description="Optional data to register as tables")],
    outputs=[CapabilityIO(name="result", type="list[dict]"), CapabilityIO(name="row_count", type="integer")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=False,
    category="data_science", tags=["sql", "duckdb", "analytics"],
)

data_stats_decl = CapabilityDeclaration(
    name="data_stats",
    description="Compute descriptive statistics for a dataset using SciPy",
    inputs=[CapabilityIO(name="data", type="list[float]"),
            CapabilityIO(name="include", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="stats", type="dict")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="data_science", tags=["statistics", "scipy"],
)

sklearn_analyze_decl = CapabilityDeclaration(
    name="sklearn_analyze",
    description="Run scikit-learn ML models (clustering, regression, classification, dimensionality reduction)",
    inputs=[CapabilityIO(name="method", type="string", description="e.g. kmeans, pca, linear_regression"),
            CapabilityIO(name="data", type="list[list]"), CapabilityIO(name="params", type="dict", required=False)],
    outputs=[CapabilityIO(name="result", type="any"), CapabilityIO(name="metrics", type="dict")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="data_science", tags=["ml", "sklearn", "learning"],
)

network_analyze_decl = CapabilityDeclaration(
    name="network_analyze",
    description="Analyze graph/network data using NetworkX",
    inputs=[CapabilityIO(name="operation", type="string", description="e.g. centrality, communities, shortest_path"),
            CapabilityIO(name="nodes", type="list[dict]"), CapabilityIO(name="edges", type="list[dict]")],
    outputs=[CapabilityIO(name="result", type="any"), CapabilityIO(name="metrics", type="dict")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=False,
    category="data_science", tags=["networkx", "graph", "network"],
)

sympy_compute_decl = CapabilityDeclaration(
    name="sympy_compute",
    description="Perform symbolic mathematics using SymPy",
    inputs=[CapabilityIO(name="expression", type="string", description="Symbolic expression or operation"),
            CapabilityIO(name="operation", type="string", description="solve, simplify, integrate, differentiate, etc.")],
    outputs=[CapabilityIO(name="result", type="any")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="data_science", tags=["sympy", "symbolic", "mathematics"],
)

jupyter_exec_decl = CapabilityDeclaration(
    name="jupyter_exec",
    description="Execute a Jupyter notebook or code cell and capture outputs",
    inputs=[CapabilityIO(name="code", type="string"),
            CapabilityIO(name="kernel", type="string", required=False, default="python3")],
    outputs=[CapabilityIO(name="outputs", type="list[dict]"), CapabilityIO(name="error", type="string")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="data_science", tags=["jupyter", "notebook", "execution"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        numpy_compute_decl, pandas_analyze_decl, polars_analyze_decl,
        duckdb_query_decl, data_stats_decl, sklearn_analyze_decl,
        network_analyze_decl, sympy_compute_decl, jupyter_exec_decl,
    ]:
        registry.register(decl)
