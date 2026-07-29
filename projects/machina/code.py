from __future__ import annotations
from capabilities.base import CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass
from capabilities.registry import CapabilityRegistry

python_execute_decl = CapabilityDeclaration(
    name="python_execute",
    description="Execute Python code in a sandboxed environment and capture output",
    inputs=[CapabilityIO(name="code", type="string", description="Python code to execute"),
            CapabilityIO(name="timeout", type="integer", required=False, default=30)],
    outputs=[CapabilityIO(name="stdout", type="string"), CapabilityIO(name="stderr", type="string"),
             CapabilityIO(name="return_code", type="integer"), CapabilityIO(name="variables", type="dict")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=False,
    category="code", tags=["python", "execution", "sandbox"],
)

ast_parse_decl = CapabilityDeclaration(
    name="ast_parse",
    description="Parse Python source code into AST and extract structure",
    inputs=[CapabilityIO(name="source", type="string", description="Python source code"),
            CapabilityIO(name="extract", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="tree", type="dict"), CapabilityIO(name="functions", type="list[dict]"),
             CapabilityIO(name="classes", type="list[dict]"), CapabilityIO(name="imports", type="list[dict]")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="code", tags=["ast", "python", "parse"],
)

tree_sitter_parse_decl = CapabilityDeclaration(
    name="tree_sitter_parse",
    description="Parse any language source code using Tree-Sitter",
    inputs=[CapabilityIO(name="source", type="string"), CapabilityIO(name="language", type="string")],
    outputs=[CapabilityIO(name="tree", type="dict"), CapabilityIO(name="syntax_nodes", type="list[dict]")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="code", tags=["tree-sitter", "parse", "syntax"],
)

git_analyze_decl = CapabilityDeclaration(
    name="git_analyze",
    description="Analyze a Git repository: log, diff, blame, branches, contributors",
    inputs=[CapabilityIO(name="path", type="string", description="Path to git repository"),
            CapabilityIO(name="operation", type="string")],
    outputs=[CapabilityIO(name="result", type="any"), CapabilityIO(name="summary", type="dict")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="code", tags=["git", "repository", "analysis"],
)

code_metrics_decl = CapabilityDeclaration(
    name="code_metrics",
    description="Compute code quality metrics: cyclomatic complexity, lines, coverage",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="metrics", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="metrics", type="dict"), CapabilityIO(name="violations", type="list[dict]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="code", tags=["metrics", "complexity", "quality"],
)

code_lint_decl = CapabilityDeclaration(
    name="code_lint",
    description="Lint Python code using Ruff",
    inputs=[CapabilityIO(name="source", type="string"), CapabilityIO(name="rules", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="issues", type="list[dict]"), CapabilityIO(name="error_count", type="integer")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="code", tags=["lint", "ruff", "quality"],
)

code_typecheck_decl = CapabilityDeclaration(
    name="code_typecheck",
    description="Type-check Python code using Pyright/pytype",
    inputs=[CapabilityIO(name="source", type="string"), CapabilityIO(name="strict", type="boolean", required=False, default=False)],
    outputs=[CapabilityIO(name="errors", type="list[dict]"), CapabilityIO(name="warnings", type="list[dict]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="code", tags=["types", "typecheck", "pyright"],
)

dependency_graph_decl = CapabilityDeclaration(
    name="dependency_graph",
    description="Analyze and visualize dependency graphs in a codebase",
    inputs=[CapabilityIO(name="path", type="string"),
            CapabilityIO(name="depth", type="integer", required=False, default=3)],
    outputs=[CapabilityIO(name="dependencies", type="list[dict]"), CapabilityIO(name="cycles", type="list[list]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="code", tags=["dependencies", "graph", "analysis"],
)

diff_analyze_decl = CapabilityDeclaration(
    name="diff_analyze",
    description="Analyze code diffs and generate structured summaries",
    inputs=[CapabilityIO(name="diff", type="string"),
            CapabilityIO(name="context_lines", type="integer", required=False, default=3)],
    outputs=[CapabilityIO(name="summary", type="dict"), CapabilityIO(name="changed_files", type="list[dict]")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="code", tags=["diff", "changes", "analysis"],
)

repo_analyze_decl = CapabilityDeclaration(
    name="repo_analyze",
    description="Analyze a repository structure: files, languages, size, dependencies",
    inputs=[CapabilityIO(name="path", type="string")],
    outputs=[CapabilityIO(name="structure", type="dict"), CapabilityIO(name="languages", type="dict"),
             CapabilityIO(name="file_count", type="integer")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="code", tags=["repository", "structure", "analysis"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        python_execute_decl, ast_parse_decl, tree_sitter_parse_decl,
        git_analyze_decl, code_metrics_decl, code_lint_decl,
        code_typecheck_decl, dependency_graph_decl, diff_analyze_decl,
        repo_analyze_decl,
    ]:
        registry.register(decl)
