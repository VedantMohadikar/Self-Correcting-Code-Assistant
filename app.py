"""
app.py — CodeFix AI v3
Run: streamlit run app.py
"""

import time
import streamlit as st
from graph import build_graph

st.set_page_config(page_title="CodeFix AI", page_icon="⟳", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
.app-title {
    font-size: 2rem; font-weight: 800; letter-spacing: -0.03em;
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-subtitle { color: #6b7280; font-size: 0.85rem; margin-top: 2px; margin-bottom: 0.5rem; }
.step-label {
    font-size: 11px; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; margin: 12px 0 4px;
}
.analysis-box {
    background: #0f0f1e; border-left: 3px solid #f87171;
    border-radius: 0 8px 8px 0; padding: 12px 16px;
    font-size: 12.5px; color: #e2e8f0;
    white-space: pre-wrap; font-family: monospace; line-height: 1.7;
}
.attempt-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px;
}
.chip {
    display: inline-block; padding: 3px 12px; border-radius: 20px;
    font-size: 11.5px; font-weight: 600;
}
.chip-pass    { background:rgba(16,185,129,.15); color:#34d399; border:1px solid rgba(16,185,129,.3); }
.chip-fail    { background:rgba(239,68,68,.15);  color:#f87171; border:1px solid rgba(239,68,68,.3); }
.chip-running { background:rgba(245,158,11,.12); color:#fbbf24; border:1px solid rgba(245,158,11,.3); }
.final-pass { background:rgba(16,185,129,.08); border:1px solid rgba(16,185,129,.3); border-radius:12px; padding:1rem 1.2rem; }
.final-fail { background:rgba(239,68,68,.08);  border:1px solid rgba(239,68,68,.3);  border-radius:12px; padding:1rem 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ── RENDER FUNCTION (defined here so it's available everywhere below) ──────────
def _render_results(r):
    for att in r["attempts"]:
        chip_cls  = {"pass":"chip-pass","fail":"chip-fail","running":"chip-running"}.get(att["overall_status"],"chip-running")
        chip_text = {"pass":"✓ PASS","fail":"✗ FAIL","running":"⟳ Running"}.get(att["overall_status"],"⟳")

        st.markdown(f"""
        <div class='attempt-header'>
            <span style='font-size:14px;font-weight:700;color:#9ca3af;'>Attempt {att["num"]}</span>
            <span class='chip {chip_cls}'>{chip_text}</span>
        </div>""", unsafe_allow_html=True)

        # ② GENERATED CODE
        st.markdown("<div class='step-label' style='color:#a78bfa;'>② Generated Code</div>", unsafe_allow_html=True)
        st.code(att.get("code",""), language="python")

        # ① TEST CASES — shown right after code, before execution
        if r.get("generated_tests"):
            label = "① Test Cases (auto-generated)" if not r.get("test_code_was_provided") else "① Test Cases (provided)"
            st.markdown(f"<div class='step-label' style='color:#818cf8;'>{label}</div>", unsafe_allow_html=True)
            st.code(r["generated_tests"], language="python")

        # ③ EXECUTION
        if att.get("exec_output"):
            exec_ok = att.get("exec_status") == "ok"
            color   = "#34d399" if exec_ok else "#f87171"
            label   = "✓ Executed Successfully" if exec_ok else "✗ Execution Crashed"
            st.markdown(f"<div class='step-label' style='color:{color};'>③ {label}</div>", unsafe_allow_html=True)
            if exec_ok:
                st.success(att["exec_output"])
            else:
                st.error(att["exec_output"])

        # ④ TEST RESULTS
        if att.get("test_output"):
            test_ok = att.get("test_status") == "success"
            color   = "#34d399" if test_ok else "#f87171"
            label   = "✓ All Tests Passed" if test_ok else "✗ Tests Failed"
            st.markdown(f"<div class='step-label' style='color:{color};'>④ {label}</div>", unsafe_allow_html=True)
            if test_ok:
                st.success(att["test_output"][:4000])
            else:
                st.error(att["test_output"][:4000])

        # ⑤ ERROR ANALYSIS
        if att.get("analysis"):
            st.markdown("<div class='step-label' style='color:#f87171;'>⑤ Error Analysis → Rewriting</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='analysis-box'>{att['analysis']}</div>", unsafe_allow_html=True)

        st.markdown("---")

    # FINAL RESULT
    if r.get("elapsed", 0) > 0:
        passed = r["final_status"] == "success"
        if passed:
            st.markdown(f"""<div class='final-pass'>
            <div style='font-size:16px;font-weight:700;color:#34d399;'>✓ All Tests Passed</div>
            <div style='font-size:12px;color:#6b7280;margin-top:4px;'>
            {r["total_attempts"]} attempt{"s" if r["total_attempts"]!=1 else ""} · {r["elapsed"]}s · Llama-3.3-70B</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class='final-fail'>
            <div style='font-size:16px;font-weight:700;color:#f87171;'>✗ Could Not Fix After {r["total_attempts"]} Attempts</div>
            <div style='font-size:12px;color:#6b7280;margin-top:4px;'>Try increasing Max Attempts or refine the task.</div>
            </div>""", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Attempts Used",  f"{r['total_attempts']}")
        m2.metric("Time Elapsed",   f"{r['elapsed']}s")
        m3.metric("Tests",          "Auto-generated" if not r.get("test_code_was_provided") else "User-provided")
        m4.metric("Result",         "✓ Passed" if passed else "✗ Failed")

        st.markdown("#### Final Code")
        st.code(r.get("final_code",""), language="python")


# ── EXAMPLES ───────────────────────────────────────────────────────────────────
EXAMPLES = {
    "🔢 Roman Numerals": {
        "task": "Write a function int_to_roman(num) that converts an integer (1-3999) to its Roman numeral string representation.",
        "tests": "",
    },
    "📋 Find Duplicates": {
        "task": "Write a function find_duplicates(lst) that returns a list of all elements that appear more than once. Each duplicate appears only once in the result.",
        "tests": "",
    },
    "🔀 Merge Intervals": {
        "task": "Write a function merge_intervals(intervals) that takes a list of [start, end] pairs and merges all overlapping intervals.",
        "tests": "",
    },
    "🔗 Balanced Brackets": {
        "task": "Write a function is_balanced(s) that returns True if all parentheses (), square brackets [], and curly braces {} are balanced.",
        "tests": "",
    },
    "🌳 Binary Search Tree": {
        "task": "Write a BinarySearchTree class with insert(val), search(val), and inorder() methods. inorder() returns all values in sorted order.",
        "tests": "",
    },
    "✍️ Custom Task": {"task": "", "tests": ""},
}

# ── SESSION STATE INIT ─────────────────────────────────────────────────────────
# Yeh key hai — sab results yahan store honge taaki click karne pe gayab na ho
if "results" not in st.session_state:
    st.session_state.results = None   # None = koi run nahi hua abhi

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⟳ CodeFix AI")
    st.markdown("<div style='color:#6b7280;font-size:12px;margin-bottom:1rem;'>Self-Correcting Code Agent v3</div>", unsafe_allow_html=True)
    st.divider()

    selected = st.selectbox("Quick Example", list(EXAMPLES.keys()), index=0)
    ex = EXAMPLES[selected]
    st.divider()

    task = st.text_area("Task Description", value=ex["task"], height=130,
        placeholder="Describe what you want in plain English...")

    st.markdown("<div style='font-size:11px;color:#6b7280;margin-bottom:4px;'>Test Cases <span style='color:#8b5cf6;'>(optional — leave blank to auto-generate)</span></div>", unsafe_allow_html=True)
    test_code = st.text_area("tc", value=ex["tests"], height=140,
        placeholder="def test_example():\n    assert my_fn(2) == 4\n\n# Leave blank — agent auto-generates",
        label_visibility="collapsed")

    st.divider()
    has_broken = st.checkbox("I have broken code to fix")
    broken_code = ""
    if has_broken:
        broken_code = st.text_area("Paste Broken Code", height=140)

    max_attempts = st.slider("Max Attempts", min_value=2, max_value=8, value=5)
    st.divider()

    run_clicked = st.button("▶  Run Agent", type="primary", use_container_width=True)

    st.markdown("""
    <div style='margin-top:1.5rem;font-size:11px;color:#4b5563;line-height:1.9;'>
    <b style='color:#6b7280;'>Pipeline</b><br>
    <span style='color:#818cf8;'>①</span> Auto-generate test cases<br>
    <span style='color:#a78bfa;'>②</span> Generate code<br>
    <span style='color:#fbbf24;'>③</span> Execute code (crash check)<br>
    <span style='color:#2dd4bf;'>④</span> Run pytest tests<br>
    <span style='color:#f87171;'>⑤</span> Analyze error → rewrite<br>
    <span style='color:#34d399;'>⑥</span> Repeat until pass ✓
    </div>""", unsafe_allow_html=True)

# ── MAIN ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="app-title">CodeFix AI</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Autonomous Code Generation · Self-Correction · Zero Manual Testing</div>', unsafe_allow_html=True)

# ── EMPTY STATE ────────────────────────────────────────────────────────────────
if not run_clicked and st.session_state.results is None:
    st.markdown("---")
    cols = st.columns(5)
    steps = [
        ("①","#818cf8","Generate\nTests","Auto-writes pytest cases"),
        ("②","#a78bfa","Generate\nCode","LLM writes solution"),
        ("③","#fbbf24","Execute\nCode","Syntax/runtime check"),
        ("④","#2dd4bf","Run\nTests","pytest validation"),
        ("⑤","#f87171","Analyze\n& Fix","Structured diagnosis"),
    ]
    for col, (num, color, label, sub) in zip(cols, steps):
        col.markdown(f"""
        <div style='text-align:center;padding:1rem .5rem;background:#0f0f1e;border:1px solid #1e1e38;border-radius:12px;'>
        <div style='font-size:1.4rem;font-weight:700;color:{color};'>{num}</div>
        <div style='font-size:12px;font-weight:600;color:#e2e8f0;margin-top:6px;white-space:pre-line;'>{label}</div>
        <div style='font-size:10.5px;color:#6b7280;margin-top:5px;'>{sub}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("""<div style='text-align:center;color:#4b5563;font-size:13px;padding:1.5rem;'>
    Pick a task and click <b style='color:#8b5cf6;'>▶ Run Agent</b>. Test cases are <b style='color:#8b5cf6;'>auto-generated</b>.
    </div>""", unsafe_allow_html=True)

# ── RUN AGENT ──────────────────────────────────────────────────────────────────
if run_clicked:
    if not task.strip():
        st.error("⚠️ Please enter a task description.")
        st.stop()

    # Reset previous results
    st.session_state.results = {
        "attempts": [],
        "generated_tests": "",
        "final_code": "",
        "final_status": "pending",
        "elapsed": 0,
        "total_attempts": 0,
        "test_code_was_provided": bool(test_code.strip()),
    }

    st.markdown("---")
    status_bar   = st.empty()
    progress_bar = st.progress(0)
    live_area    = st.empty()

    def render_live(results):
        with live_area.container():
            _render_results(results)

    agent = build_graph()
    initial_state = {
        "task": task,
        "test_code": test_code.strip() if test_code.strip() else None,
        "broken_code": broken_code.strip() if broken_code.strip() else None,
        "generated_tests": None,
        "code": "",
        "execution_status": None,
        "execution_output": None,
        "test_output": None,
        "error_log": None,
        "error_analysis": None,
        "attempt": 0,
        "max_attempts": max_attempts,
        "status": "pending",
    }

    r = st.session_state.results
    current_attempt = 0
    start_time = time.time()

    try:
        for event in agent.stream(initial_state):
            node_name = list(event.keys())[0]
            node_data = event[node_name]

            if node_name == "generate_tests":
                r["generated_tests"] = node_data.get("generated_tests", "")
                status_bar.info("① Generating test cases...")
                progress_bar.progress(10)

            elif node_name == "generate_code":
                current_attempt = node_data["attempt"]
                r["attempts"].append({
                    "num": current_attempt,
                    "code": node_data["code"],
                    "overall_status": "running",
                    "exec_status": None, "exec_output": None,
                    "test_status": None, "test_output": None,
                    "analysis": None,
                })
                r["final_code"] = node_data["code"]
                status_bar.info(f"② Attempt {current_attempt}/{max_attempts} — Generating code...")
                progress_bar.progress(min(20 + current_attempt * 15, 80))
                render_live(r)

            elif node_name == "execute_code":
                r["attempts"][-1]["exec_status"]  = node_data.get("execution_status")
                r["attempts"][-1]["exec_output"]  = node_data.get("execution_output", "")
                if node_data.get("execution_status") == "error":
                    r["attempts"][-1]["overall_status"] = "fail"
                    status_bar.warning(f"③ Execution crashed — analyzing...")
                else:
                    status_bar.info(f"③ Executed OK — running tests...")
                render_live(r)

            elif node_name == "run_tests":
                test_status = node_data["status"]
                r["attempts"][-1]["test_status"]   = test_status
                r["attempts"][-1]["test_output"]   = node_data.get("test_output", "")
                r["attempts"][-1]["overall_status"] = "pass" if test_status == "success" else "fail"
                r["final_status"] = test_status
                if test_status == "success":
                    status_bar.success(f"④ All tests passed on attempt {current_attempt}! ✓")
                    progress_bar.progress(100)
                else:
                    remaining = max_attempts - current_attempt
                    status_bar.warning(f"④ Tests failed — {remaining} retries left...")
                render_live(r)

            elif node_name == "analyze_error":
                r["attempts"][-1]["analysis"] = node_data.get("error_analysis", "")
                status_bar.warning("⑤ Analyzing error — rewriting code...")
                render_live(r)

    except Exception as e:
        status_bar.error(f"Agent error: {e}")
        st.exception(e)
        st.stop()

    r["elapsed"] = round(time.time() - start_time, 1)
    r["total_attempts"] = current_attempt
    render_live(r)

# ── RENDER SAVED RESULTS (persists across clicks) ──────────────────────────────
elif st.session_state.results is not None:
    st.markdown("---")
    _render_results(st.session_state.results)