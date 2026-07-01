# lathe-generated module — do not edit by hand

def _strip_code_fences_impl(text):
    s = text.strip()
    if not s:
        return ""
    fence = chr(96) * 3
    lines = s.split("\n")
    if lines[0].strip().startswith(fence):
        lines = lines[1:]
    if lines and lines[-1].strip() == fence:
        lines = lines[:-1]
    return "\n".join(lines).strip()


def classify_error_type(error_msg: str) -> str:
    msg = error_msg.lower()
    if "syntaxerror" in msg:
        return "syntax_error"
    if "assertionerror" in msg:
        return "assertion_error"
    if "importerror" in msg or "modulenotfounderror" in msg:
        return "import_error"
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    return "unknown"

def plan_completion_ratio(planned: list, completed: list) -> float:
    if not planned:
        return 0.0
    completed_set = set(completed)
    count = sum(1 for name in planned if name in completed_set)
    return round(count / len(planned), 4)

def strip_code_fences(text: str) -> str:
    return _strip_code_fences_impl(text)

def pick_weakest_functions(fn_records: list, threshold: int) -> list:
    filtered = [r for r in fn_records if r["test_count"] < threshold]
    filtered.sort(key=lambda r: r["test_count"])
    return [r["name"] for r in filtered]

