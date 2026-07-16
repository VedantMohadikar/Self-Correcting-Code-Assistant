import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .state import AgentState

load_dotenv()

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def _strip_fences(code: str) -> str:
    code = code.strip()
    if not code.startswith("```"):
        return code
    lines = code.split("\n")
    end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
    body = "\n".join(lines[1:end]).strip()
    return body[7:] if body.startswith("python\n") else body


def _detect_code_type(task: str) -> str:
    task_lower = task.lower()
    if any(w in task_lower for w in ["class", "oop", "object", "inherit"]):
        return "class"
    if any(w in task_lower for w in ["script", "cli", "command", "file", "read", "write", "parse"]):
        return "script"
    if any(w in task_lower for w in ["function", "method", "def ", "return"]):
        return "function"
    return "general"


def generate_code(state: AgentState) -> dict:
    code_type = _detect_code_type(state["task"])

    broken = state.get("broken_code") or ""
    analysis = state.get("error_analysis") or ""

    if state["attempt"] == 0 and broken.strip():
        prompt = (
            f'Fix this broken Python code completely.\n'
            f'Task: "{state["task"]}"\n\n'
            f'Broken code:\n{broken}\n\n'
            f'Return ONLY the corrected Python code. No explanation. No markdown fences.'
        )

    elif analysis.strip():
        prompt = f"""You are fixing a Python solution.

Task: "{state["task"]}"

Your previous code:
{state["code"]}

Error diagnosis:
{analysis}

Rewrite the complete solution addressing all points in the diagnosis.
Return ONLY the Python code. No explanation. No markdown fences."""

    else:
        type_hints = {
            "function": "Write one or more Python functions. Include all edge case handling.",
            "class": "Write a complete Python class with all necessary methods and proper __init__.",
            "script": "Write a complete, runnable Python script. Include a if __name__ == '__main__': block.",
            "general": "Write complete, production-quality Python code.",
        }
        prompt = f"""You are an expert Python developer.

Task: "{state["task"]}"

{type_hints[code_type]}

Requirements:
- Complete, runnable code
- Handle edge cases (None, empty, 0, negative numbers)
- Use only Python standard library unless task requires external packages
- No explanation, no markdown fences, ONLY the Python code"""

    raw = _llm.invoke(prompt).content.strip()
    code = _strip_fences(raw)

    return {
        "code": code,
        "attempt": state["attempt"] + 1,
        "error_analysis": None,
    }