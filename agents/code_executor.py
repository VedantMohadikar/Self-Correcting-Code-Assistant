"""
agents/code_executor.py
------------------------
LangGraph node: directly runs the generated code with `python solution.py`.

Why this runs BEFORE pytest:
  - Catches syntax errors, import errors, top-level crashes FAST
  - If code can't even run, there's no point running tests
  - Gives cleaner error signal to error_analyzer (pure crash vs test failure)

Handles two cases:
  1. Code is a script  → run it, check exit code
  2. Code defines functions/classes only → wrap in a minimal runner to check imports

Output:
  - execution_status: "ok" | "error"
  - execution_output: stdout + stderr (shown in UI)
  - error_log: set to execution error if crashed (feeds error_analyzer)
"""

import os
import subprocess
import tempfile
from .state import AgentState


# Minimal wrapper to test that functions/classes at least import without error
_IMPORT_CHECK = """
import sys
try:
    exec(open("solution.py").read())
    print("[executor] Code loaded successfully.")
except Exception as e:
    print(f"[executor] Load error: {e}", file=sys.stderr)
    sys.exit(1)
"""


def execute_code(state: AgentState) -> dict:
    """Returns: {"execution_status", "execution_output", optionally "error_log"}"""

    code = state["code"]

    with tempfile.TemporaryDirectory() as tmp:
        sol_path = os.path.join(tmp, "solution.py")
        with open(sol_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Decide run mode:
        # - If code has if __name__ == '__main__' → run it directly (it's a script)
        # - Otherwise → run the import-check wrapper (it's a library/function file)
        if '__name__' in code and '__main__' in code:
            cmd = ["python", "solution.py"]
        else:
            check_path = os.path.join(tmp, "_check.py")
            with open(check_path, "w") as f:
                f.write(_IMPORT_CHECK)
            cmd = ["python", "_check.py"]

        try:
            result = subprocess.run(
                cmd,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            return {
                "execution_status": "error",
                "execution_output": "Execution timed out after 10 seconds (possible infinite loop).",
                "error_log": "TimeoutError: Code execution exceeded 10 seconds.",
            }

        output = (result.stdout + result.stderr).strip()

        if result.returncode == 0:
            return {
                "execution_status": "ok",
                "execution_output": output or "(ran successfully, no output)",
            }
        else:
            return {
                "execution_status": "error",
                "execution_output": output,
                "error_log": output,
            }
