from __future__ import annotations
from capabilities.base import CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass
from capabilities.registry import CapabilityRegistry

optimize_problem_decl = CapabilityDeclaration(
    name="optimize_problem",
    description="Solve optimization problems using CVXPY or OR-Tools",
    inputs=[CapabilityIO(name="problem_type", type="string", description="lp, milp, convex, constraint_satisfaction"),
            CapabilityIO(name="objective", type="dict"), CapabilityIO(name="constraints", type="list[dict]"),
            CapabilityIO(name="variables", type="list[dict]")],
    outputs=[CapabilityIO(name="solution", type="dict"), CapabilityIO(name="status", type="string"),
             CapabilityIO(name="objective_value", type="float")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="scientific", tags=["optimization", "cvxpy", "or-tools"],
)

z3_verify_decl = CapabilityDeclaration(
    name="z3_verify",
    description="Verify logical constraints and solve SMT problems using Z3",
    inputs=[CapabilityIO(name="constraints", type="list[string]"),
            CapabilityIO(name="variables", type="list[string]")],
    outputs=[CapabilityIO(name="sat", type="boolean"), CapabilityIO(name="model", type="dict"),
             CapabilityIO(name="proof", type="list[string]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=False,
    category="scientific", tags=["z3", "smt", "verification"],
)

monte_carlo_decl = CapabilityDeclaration(
    name="monte_carlo",
    description="Run Monte Carlo simulations for uncertainty estimation",
    inputs=[CapabilityIO(name="simulate_func", type="string", description="Python function defining the simulation"),
            CapabilityIO(name="num_trials", type="integer", default=1000),
            CapabilityIO(name="param_distributions", type="dict")],
    outputs=[CapabilityIO(name="results", type="list[float]"), CapabilityIO(name="statistics", type="dict"),
             CapabilityIO(name="confidence_intervals", type="dict")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="scientific", tags=["monte_carlo", "simulation", "uncertainty"],
)

statistical_test_decl = CapabilityDeclaration(
    name="statistical_test",
    description="Run statistical tests: t-test, chi-squared, ANOVA, Mann-Whitney, etc.",
    inputs=[CapabilityIO(name="test", type="string", description="Name of statistical test"),
            CapabilityIO(name="sample_a", type="list[float]"),
            CapabilityIO(name="sample_b", type="list[float]", required=False),
            CapabilityIO(name="alpha", type="float", required=False, default=0.05)],
    outputs=[CapabilityIO(name="statistic", type="float"), CapabilityIO(name="p_value", type="float"),
             CapabilityIO(name="significant", type="boolean"), CapabilityIO(name="effect_size", type="float")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="scientific", tags=["statistics", "hypothesis_testing"],
)

confidence_estimate_decl = CapabilityDeclaration(
    name="confidence_estimate",
    description="Compute confidence intervals and Bayesian credible intervals",
    inputs=[CapabilityIO(name="data", type="list[float]"),
            CapabilityIO(name="method", type="string", required=False, default="bootstrap"),
            CapabilityIO(name="confidence_level", type="float", required=False, default=0.95)],
    outputs=[CapabilityIO(name="lower", type="float"), CapabilityIO(name="upper", type="float"),
             CapabilityIO(name="point_estimate", type="float"), CapabilityIO(name="method", type="string")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="scientific", tags=["confidence", "statistics", "bayesian"],
)

sensitivity_analysis_decl = CapabilityDeclaration(
    name="sensitivity_analysis",
    description="Perform sensitivity analysis on a model or function",
    inputs=[CapabilityIO(name="func", type="string"), CapabilityIO(name="parameters", type="dict"),
            CapabilityIO(name="method", type="string", required=False, default="sobol")],
    outputs=[CapabilityIO(name="sensitivities", type="dict"), CapabilityIO(name="ranking", type="list[dict]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="scientific", tags=["sensitivity", "analysis"],
)

simulation_decl = CapabilityDeclaration(
    name="simulation",
    description="Run domain-specific simulations (specify type in input)",
    inputs=[CapabilityIO(name="sim_type", type="string", description="Type of simulation"),
            CapabilityIO(name="params", type="dict")],
    outputs=[CapabilityIO(name="results", type="dict"), CapabilityIO(name="diagnostics", type="dict")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="scientific", tags=["simulation", "modelling"],
)

mathematical_prove_decl = CapabilityDeclaration(
    name="mathematical_prove",
    description="Attempt to prove or verify mathematical statements",
    inputs=[CapabilityIO(name="statement", type="string"), CapabilityIO(name="assumptions", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="result", type="string"), CapabilityIO(name="proof_steps", type="list[string]"),
             CapabilityIO(name="confidence", type="float")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="scientific", tags=["mathematics", "proof", "verification"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        optimize_problem_decl, z3_verify_decl, monte_carlo_decl,
        statistical_test_decl, confidence_estimate_decl,
        sensitivity_analysis_decl, simulation_decl, mathematical_prove_decl,
    ]:
        registry.register(decl)
