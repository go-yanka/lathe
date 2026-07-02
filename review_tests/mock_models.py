"""Dual-role mock OpenAI-compatible endpoint for testing Lathe without real LLMs.

The completions are deterministic, reviewer-authored implementations — this tests the HARNESS
(validator, sandbox, gates, pins, repair loop, CLI), not model quality.

  python review_tests/mock_models.py impl 8089     # implementer  (LOCAL_OPENAI_URL)
  python review_tests/mock_models.py analyst 8787  # analyst      (HARNESS_CLAUDE_URL)

Every prompt is appended to review_tests/_prompts_<role>.log for auditability.
"""
import sys, json, re, os
from http.server import BaseHTTPRequestHandler, HTTPServer

ROLE = sys.argv[1] if len(sys.argv) > 1 else "impl"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else (8089 if ROLE == "impl" else 8787)
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_prompts_%s.log" % ROLE)

IMPL = {
    "add": "def add(a, b):\n    return a + b",
    "is_even": "def is_even(n):\n    return n % 2 == 0",
    "fizzbuzz": ("def fizzbuzz(n):\n    if n % 15 == 0:\n        return 'FizzBuzz'\n"
                 "    if n % 3 == 0:\n        return 'Fizz'\n    if n % 5 == 0:\n        return 'Buzz'\n"
                 "    return str(n)"),
    "greet": ("def greet(name):\n    if not name:\n        return 'Hello, world!'\n"
              "    return 'Hello, ' + name + '!'"),
    "token_overlap": ("def token_overlap(a, b):\n    a = a or ''\n    b = b or ''\n"
                      "    return len(set(a.lower().split()) & set(b.lower().split()))"),
    "parse_duration": ("def parse_duration(s):\n    import re\n    total = 0\n"
                       "    for val, unit in re.findall(r'(\\d+)([hms])', s or ''):\n"
                       "        total += int(val) * {'h': 3600, 'm': 60, 's': 1}[unit]\n    return total"),
    "parse_amount": ("def parse_amount(s):\n    try:\n        if s is None:\n            return 0.0\n"
                     "        t = str(s).strip().lstrip('$').replace(',', '')\n        return float(t) if t else 0.0\n"
                     "    except Exception:\n        return 0.0"),
    "parse_entry": ("def parse_entry(line):\n    if not line:\n        return None\n"
                    "    parts = [p.strip() for p in str(line).split(',')]\n    if len(parts) < 3:\n        return None\n"
                    "    def _amt(s):\n        try:\n            t = s.strip().lstrip('$').replace(',', '')\n"
                    "            return float(t) if t else 0.0\n        except Exception:\n            return 0.0\n"
                    "    return {'date': parts[0], 'category': parts[1], 'amount': _amt(parts[2])}"),
    "total": ("def total(entries):\n    if not entries:\n        return 0.0\n"
              "    return float(sum(e.get('amount', 0.0) for e in entries if isinstance(e, dict)))"),
    "by_category": ("def by_category(entries):\n    out = {}\n    if not entries:\n        return out\n"
                    "    for e in entries:\n        if isinstance(e, dict):\n"
                    "            out[e.get('category')] = out.get(e.get('category'), 0.0) + float(e.get('amount', 0.0))\n"
                    "    return out"),
    "top_category": ("def top_category(entries):\n    if not entries:\n        return None\n"
                     "    sums = {}\n    for e in entries:\n        if isinstance(e, dict):\n"
                     "            sums[e.get('category')] = sums.get(e.get('category'), 0.0) + float(e.get('amount', 0.0))\n"
                     "    return max(sums, key=sums.get) if sums else None"),
    "summarize": ("def summarize(lines):\n    from ledger_core import parse_entry\n"
                  "    from ledger_stats import total, by_category, top_category\n"
                  "    entries = [e for e in (parse_entry(l) for l in (lines or [])) if e]\n"
                  "    if not entries:\n        return {'total': 0.0, 'by_category': {}, 'top': None}\n"
                  "    return {'total': total(entries), 'by_category': by_category(entries), 'top': top_category(entries)}"),
}


def implement(prompt):
    m = re.search(r"(?:function|Implement|Write)\s+`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\(", prompt)
    name = m.group(1) if m else None
    if name in IMPL:
        return "```python\n%s\n```" % IMPL[name]
    for n, code in IMPL.items():
        if re.search(r"\b%s\s*\(" % re.escape(n), prompt):
            return "```python\n%s\n```" % code
    return "```python\n# mock: unknown function requested\n```"


PLAN = (
    'OUT_DIR = "examples/_agent_build"\n'
    'MODULE_NAME = "durations"\n'
    'HEADER = "import re"\n'
    'FUNCTIONS = [\n'
    '    {\n'
    '        "name": "parse_duration",\n'
    '        "prompt": "Write parse_duration(s): parse \'2h30m\'/\'90s\' to seconds via re.findall (\\\\d+)([hms]).",\n'
    '        "tests": [\n'
    '            "assert parse_duration(\'2h30m\') == 9000",\n'
    '            "assert parse_duration(\'90s\') == 90",\n'
    '            "assert parse_duration(\'1h\') == 3600",\n'
    '            "assert parse_duration(\'\') == 0",\n'
    '        ],\n'
    '    },\n'
    ']\n'
)

REVIEW_FINDINGS = (
    "REVIEW FINDINGS (mock analyst):\n"
    "1. [advisory] No blocking defects found in the reviewed file(s).\n"
    "2. The review was performed by a deterministic stand-in analyst for harness testing;\n"
    "   treat these findings as plumbing-verification, not real analysis.\n"
)


def analyze(prompt):
    if "OBJECTIVE:" in prompt or "next plan" in prompt.lower():
        return "```python\n%s```" % PLAN
    return REVIEW_FINDINGS


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send({"status": "ok", "data": [{"id": "mock"}]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            prompt = json.loads(raw)["messages"][-1]["content"]
            if isinstance(prompt, list):
                prompt = "".join(b.get("text", "") for b in prompt if isinstance(b, dict))
        except Exception:
            prompt = raw.decode("utf-8", "replace")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\n== %s ==\n%s\n" % (ROLE, prompt[:1500]))
        content = analyze(prompt) if ROLE == "analyst" else implement(prompt)
        self._send({"choices": [{"message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4}})


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
