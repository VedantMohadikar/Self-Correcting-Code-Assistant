"""
agents/test_runner.py
----------------------
LangGraph node: runs pytest against the generated code.

Only called when execute_code passes (no crash).
Uses `generated_tests` (auto-generated or user-provided via test_generator node).

Why separate from code_executor:
  - executor = "does it run at all?"
  - test_runner = "does it produce correct results?"
  Two different failure modes → different error signals for error_analyzer.
"""

import os
import subprocess
import tempfile
from .state import AgentState


def run_tests(state: AgentState) -> dict:
    """Returns: {"status", "error_log", "test_output"}"""

    # Use auto-generated tests (test_generator always populates this)
    tests = state.get("generated_tests", "").strip()

    if not tests:
        # No tests available — treat execution success as full pass
        return {
            "status": "success",
            "error_log": None,
            "test_output": "No test cases — code executed without errors.",
        }

    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "solution.py"), "w", encoding="utf-8") as f:
            f.write(state["code"])

        with open(os.path.join(tmp, "test_solution.py"), "w", encoding="utf-8") as f:
            f.write("from solution import *\n\n")
            f.write(tests)

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "test_solution.py", "-v",
                 "--tb=short", "--no-header", "-q"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "pending",
                "error_log": "pytest timed out after 20 seconds.",
                "test_output": "Tests timed out.",
            }

        full_output = (result.stdout + result.stderr).strip()

        if result.returncode == 0:
            return {
                "status": "success",
                "error_log": None,
                "test_output": full_output,
            }
        else:
            trimmed = "\n".join(full_output.splitlines()[-50:])
            return {
                "status": "pending",
                "error_log": trimmed,
                "test_output": full_output,
            }
