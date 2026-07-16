"""
agents/error_analyzer.py
-------------------------
LangGraph node: diagnoses WHY the code failed before the next generation attempt.

Why a dedicated analyzer node?
  - Raw traceback → code_generator = LLM tries to fix blindly
  - Structured diagnosis → code_generator = LLM knows EXACTLY what to fix

The analysis output feeds code_generator's retry prompt as `error_analysis`.

Runs after:
  - code_executor if execution crashed
  - run_tests if pytest failed
"""

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .state import AgentState

load_dotenv()

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def analyze_error(state: AgentState) -> dict:
    """Returns: {"error_analysis": str}"""

    # Build context: what failed and what the output was
    error_context = state.get("error_log") or state.get("execution_output") or "Unknown error"

    # Distinguish crash vs test failure for better diagnosis
    if state.get("execution_status") == "error":
        failure_type = "The code crashed during execution (before tests could run)."
    else:
        failure_type = "The code ran but failed one or more pytest test cases."

    prompt = f"""You are a Python debugging expert.

Task the code was supposed to solve:
\"\"\"{state['task']}\"\"\"

Current code:
```python
{state['code']}
```

{failure_type}

Error / test failure output:
{error_context}

Provide a concise, structured diagnosis in this exact format:

ROOT CAUSE:
<one sentence — what is fundamentally wrong>

SPECIFIC BUGS:
<bullet list of exact lines/logic that are wrong>

FIX PLAN:
<step-by-step what the rewrite must do differently>

EDGE CASES TO HANDLE:
<any edge cases the current code misses>

Keep it technical and specific. This will be used directly by the code rewriter."""

    analysis = _llm.invoke(prompt).content.strip()
    return {"error_analysis": analysis}
