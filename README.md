# Self-Correcting-Code-Assistant

Give it any task in plain English. It writes the code, generates its own test cases, executes and validates everything, and self-corrects until all tests pass — no manual testing required.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-green?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-Llama--3.3--70B-orange?style=flat-square)](https://groq.com)

---

## What It Does

Traditional AI code generation: LLM writes code → you test it → you debug it → repeat manually.

**CodeFix AI**: LLM writes code → agent tests it → agent debugs it → agent rewrites → repeats automatically.

```
You type:   "Write a function that finds all duplicates in a list"
Agent does: generates tests → writes code → runs tests → fixes errors → passes ✓
You get:    working, tested Python code
```

---

## Pipeline Architecture

```mermaid
graph TD
    A([User: Task Description]) --> B

    B["🧪 generate_tests\nAuto-write pytest cases from task"]
    B --> C

    C["✍️ generate_code\nLLM writes Python solution"]
    C --> D

    D["⚡ execute_code\nRun code directly — catch crashes"]
    D -->|Execution crashed| E
    D -->|Ran successfully| F

    F["🔬 run_tests\nRun pytest with generated test cases"]
    F -->|All tests PASS| G
    F -->|Tests FAIL + retries left| E
    F -->|Tests FAIL + max attempts| G

    E["🔍 analyze_error\nStructured diagnosis: root cause + fix plan"]
    E --> C

    G(["✅ END: Return final code + metrics"])

    style A fill:#1e1e3a,color:#e2e8f0,stroke:#6d28d9
    style B fill:#1e1e3a,color:#818cf8,stroke:#818cf8
    style C fill:#1e1e3a,color:#a78bfa,stroke:#a78bfa
    style D fill:#1e1e3a,color:#fbbf24,stroke:#fbbf24
    style E fill:#1e1e3a,color:#f87171,stroke:#f87171
    style F fill:#1e1e3a,color:#2dd4bf,stroke:#2dd4bf
    style G fill:#1e1e3a,color:#34d399,stroke:#34d399
```

---

## Self-Correction Loop

```mermaid
sequenceDiagram
    participant U as User
    participant ST as Streamlit UI
    participant LG as LangGraph
    participant LLM as Groq LLM
    participant PY as Python Subprocess

    U->>ST: Task description
    ST->>LG: stream(initial_state)

    LG->>LLM: Generate test cases for task
    LLM-->>LG: pytest test functions
    LG-->>ST: Test cases ready

    loop Until tests pass or max_attempts reached
        LG->>LLM: Generate or fix code
        LLM-->>LG: Python code
        LG-->>ST: Code generated

        LG->>PY: python solution.py
        PY-->>LG: stdout/stderr
        LG-->>ST: Execution result

        alt Execution crashed
            LG->>LLM: Analyze crash
            LLM-->>LG: Root cause + fix plan
            LG-->>ST: Error analysis shown
        else Executed OK
            LG->>PY: pytest test_solution.py
            PY-->>LG: test results
            LG-->>ST: Test results shown

            alt All tests pass
                LG-->>ST: Complete
            else Tests fail
                LG->>LLM: Analyze failures
                LLM-->>LG: Root cause + fix plan
                LG-->>ST: Error analysis shown
            end
        end
    end

    ST-->>U: Final code + metrics
```

---

## System Overview

```
┌───────────────────────────────────────────────────────┐
│                    USER (Browser)                     │
│         Task input · Live output · Final code         │
└───────────────────────────┬───────────────────────────┘
                            │ HTTP
                            ▼
┌───────────────────────────────────────────────────────┐
│              STREAMLIT (app.py)                       │
│  session_state persistence · live render_all()        │
└───────────────────────────┬───────────────────────────┘
                            │ Python call
                            ▼
┌───────────────────────────────────────────────────────┐
│           LANGGRAPH STATEGRAPH (graph/pipeline.py)    │
│                                                       │
│  generate_tests → generate_code → execute_code        │
│                        ▲              │               │
│                        │         crash│ok             │
│                  analyze_error   ←────┘               │
│                        ▲         run_tests            │
│                        └──────── fail│pass            │
│                                      ▼                │
│                                     END               │
└──────────────┬────────────────────────────────────────┘
               │ API calls (3 nodes)
               ▼
┌───────────────────────────────────────────────────────┐
│              GROQ API — Llama-3.3-70B                 │
│    test_generator · code_generator · error_analyzer   │
└───────────────────────────────────────────────────────┘
               │ subprocess
               ▼
┌───────────────────────────────────────────────────────┐
│         LOCAL PYTHON SUBPROCESS (isolated)            │
│      execute_code · run_tests · tempfile sandbox      │
└───────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
codefix-ai/
│
├── agents/
│   ├── state.py              ← AgentState TypedDict — shared schema
│   ├── test_generator.py     ← Node ①: auto-generates pytest cases from task
│   ├── code_generator.py     ← Node ②: writes/rewrites code (3 prompt strategies)
│   ├── code_executor.py      ← Node ③: direct python run — catches crashes early
│   ├── test_runner.py        ← Node ④: pytest in isolated subprocess
│   ├── error_analyzer.py     ← Node ⑤: structured root cause diagnosis
│   └── __init__.py
│
├── graph/
│   ├── pipeline.py           ← LangGraph StateGraph + conditional retry edges
│   └── __init__.py
│
├── .streamlit/
│   └── config.toml           ← Dark violet theme
│
├── app.py                    ← Streamlit UI (entry point)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Agent Details

| Agent | Input | Output | Uses LLM? |
|---|---|---|---|
| `test_generator` | `task` | `generated_tests` | ✅ |
| `code_generator` | `task` + `error_analysis` | `code` | ✅ |
| `code_executor` | `code` | `execution_status`, `execution_output` | ❌ |
| `test_runner` | `code` + `generated_tests` | `test_output`, `status` | ❌ |
| `error_analyzer` | `code` + `error_log` | `error_analysis` | ✅ |

3 LLM calls per retry cycle. Code execution and testing run locally — no API cost.

---

## Setup

```bash
git clone https://github.com/kunwardhruv/codefix-ai
cd codefix-ai

pip install -r requirements.txt

# Get free API key at console.groq.com
copy .env.example .env
# Add: GROQ_API_KEY=gsk_...

streamlit run app.py
```

---

## Test Cases

### Easy — first attempt pass

**Palindrome Check**
```
Write a function is_palindrome(s) that returns True if the string is a palindrome.
Ignore spaces, punctuation, and case.
"A man a plan a canal Panama" → True
```

**FizzBuzz**
```
Write a function fizzbuzz(n) that returns a list of strings 1 to n.
Multiples of 3 → "Fizz", 5 → "Buzz", both → "FizzBuzz", else number as string.
```

### Medium — 1-2 retries

**Anagram Groups**
```
Write a function group_anagrams(words) that groups anagrams together.
["eat","tea","tan","ate","nat","bat"] → [["eat","tea","ate"],["tan","nat"],["bat"]]
```

**Longest Substring Without Repeating**
```
Write a function longest_unique_substring(s) that returns the length of the longest
substring without repeating characters. "abcabcbb" → 3
```

**Flatten Nested List**
```
Write a function flatten(lst) that flattens any depth of nested lists.
[1, [2, [3, [4]], 5]] → [1, 2, 3, 4, 5]
```

**LRU Cache**
```
Write a class LRUCache(capacity) with get(key) and put(key, value) methods.
Evict least recently used when over capacity. Standard library only.
```

### Hard — multiple retries

**Valid Sudoku**
```
Write a function is_valid_sudoku(board) that takes a 9x9 grid (list of lists, "." for empty)
and returns True if no row, column, or 3x3 box has duplicate digits.
```

**Word Ladder**
```
Write a function word_ladder(begin_word, end_word, word_list) that returns the minimum
number of single-letter transformations to reach end_word. Return 0 if impossible.
```

### Edge case stress tests

**Roman Numeral Round Trip**
```
Write int_to_roman(num) and roman_to_int(s).
Must be perfect inverses: roman_to_int(int_to_roman(n)) == n for all n in 1-3999.
```

**Expression Evaluator (no eval)**
```
Write evaluate(expression) for math strings with +, -, *, / and parentheses.
No eval() allowed. "(1+2)*(3+4)" → 21. Handle operator precedence.
```

---

## Key Design Decisions

**Why generate tests before code?**
Test-first forces the LLM to reason about *what* the code must do before *how* — higher first-attempt pass rate.

**Why subprocess instead of exec()?**
`exec()` runs untrusted LLM code in-process. A bad generation can crash the entire agent. Subprocess gives full isolation + 15s timeout.

**Why a dedicated error_analyzer node?**
Raw traceback → code_generator = blind retry. Structured diagnosis (root cause + specific lines + fix plan) → targeted rewrite = fewer retries.

**Why temperature=0?**
Code needs determinism. Randomness hurts correctness here.

**Why session_state for results?**
Streamlit re-runs the whole script on every click. Without session_state, clicking any expander clears all output.

---

## Author

**Vedant Mohadikar** 

- LinkedIn: www.linkedin.com/in/vedant-mohadikar-4029a8252
- GitHub: [github.com/VedantMohadikar](https://github.com/VedantMohadikar)
- Email: mvedant1607@gmail.com
