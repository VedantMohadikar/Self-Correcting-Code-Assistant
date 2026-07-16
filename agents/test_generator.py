"""
agents/test_generator.py
-------------------------
LangGraph node: auto-generates pytest test cases from the task description.
Runs ONCE at the start of the pipeline.

If the user already provided test_code → skip generation, use theirs.
If not → LLM writes comprehensive tests covering:
  - Happy path (normal inputs)
  - Edge cases (empty, zero, negative, None)
  - Type/format checks where relevant
  - At least 5-8 test functions

Why generate tests first (before code)?
  Test-first thinking forces the LLM to reason about WHAT the code must do
  before HOW to do it → better-targeted code generation in the next node.
"""

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .state import AgentState

load_dotenv()

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def _strip_fences(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
    body = "\n".join(lines[1:end]).strip()
    return body[7:] if body.startswith("python\n") else body


def generate_tests(state: AgentState) -> dict:
    user_tests = state.get("test_code")
    if user_tests and str(user_tests).strip():
        return {"generated_tests": user_tests}

    prompt = f"""You are a senior Python engineer writing pytest test cases.

Task description:
\"\"\"{state['task']}\"\"\"

Write comprehensive pytest test functions for this task. Rules:
- Write 5-8 test functions with descriptive names (test_<what>_<scenario>)
- Cover: basic cases, edge cases, boundary values, error/invalid inputs
- Use assert statements only — no unittest, no fixtures needed
- Assume 'from solution import *' is already done — just call the functions directly
- If it's a class, instantiate it and test methods
- Do NOT include any imports
- Return ONLY the pytest code, no explanation, no markdown fences
"""

    raw = _llm.invoke(prompt).content.strip()
    tests = _strip_fences(raw)
    return {"generated_tests": tests}