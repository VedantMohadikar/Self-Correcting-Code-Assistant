"""
graph/pipeline.py
------------------
Full 5-node LangGraph pipeline.

Flow:
    generate_tests
         │
         ▼
    generate_code ◄──────────────────────────────────┐
         │                                           │
         ▼                                           │
    execute_code                                     │
         │                                           │
    ┌────┴────────────┐                              │
    │ execution_status│                              │
    │   "error"       │ "ok"                         │
    ▼                 ▼                              │
 analyze_error    run_tests                          │
    │             │       │                          │
    │           PASS     FAIL + retries left         │
    │             │       │                          │
    │             ▼       ▼                          │
    │            END   analyze_error ────────────────┘
    │                      │
    └──────────────────────┘  (after max_attempts → END)
"""

from langgraph.graph import StateGraph, END
from agents import (
    AgentState,
    generate_tests,
    generate_code,
    execute_code,
    run_tests,
    analyze_error,
)


# ── CONDITIONAL EDGE ROUTERS ───────────────────────────────────────────────────

def after_execute(state: AgentState) -> str:
    """After code_executor: crash → analyze, ok → test."""
    if state.get("execution_status") == "error":
        return "analyze"
    return "test"


def after_tests(state: AgentState) -> str:
    """After run_tests: pass → end, fail + budget → analyze, fail + no budget → end."""
    if state["status"] == "success":
        return "end"
    if state["attempt"] >= state["max_attempts"]:
        return "end"
    return "analyze"


def after_analyze(state: AgentState) -> str:
    """After error_analyzer: always regenerate (analysis is now in state)."""
    return "generate"


# ── BUILD ──────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(AgentState)

    # Register nodes
    g.add_node("generate_tests", generate_tests)
    g.add_node("generate_code",  generate_code)
    g.add_node("execute_code",   execute_code)
    g.add_node("run_tests",      run_tests)
    g.add_node("analyze_error",  analyze_error)

    # Entry point
    g.set_entry_point("generate_tests")

    # Fixed edges
    g.add_edge("generate_tests", "generate_code")
    g.add_edge("generate_code",  "execute_code")

    # Conditional: after execution
    g.add_conditional_edges(
        "execute_code",
        after_execute,
        {"analyze": "analyze_error", "test": "run_tests"},
    )

    # Conditional: after tests
    g.add_conditional_edges(
        "run_tests",
        after_tests,
        {"end": END, "analyze": "analyze_error"},
    )

    # Conditional: after analysis
    g.add_conditional_edges(
        "analyze_error",
        after_analyze,
        {"generate": "generate_code"},
    )

    return g.compile()
