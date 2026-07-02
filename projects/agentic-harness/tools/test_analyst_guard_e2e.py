"""D5a + D5b e2e (review §15) — the analyst-backend failure modes, proven at the process level.

  D5b: a REACHABLE endpoint returning a well-formed 200 with non-review junk ("I am a helpful assistant...")
       must be REJECTED by the content guard -> review fails loud (rc!=0), not a silent junk verdict.
  D5a: no usable backend at all (endpoint dead, CLI path disabled) -> fail LOUD: rc!=0 + explicit
       '[review unavailable' marker, never a fabricated review.
  sanity: a VALID review shape through the same mock IS accepted (the guard rejects junk, not reviews).
Run:  python projects/agentic-harness/tools/test_analyst_guard_e2e.py     (repo root)
"""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.dirname(HERE)
HREVIEW = os.path.join(INNER, "hreview.py")

WRONG = "I am a helpful assistant. How can I help you today? Feel free to ask me anything at all about code."
VALID = "HIGH | target.py:3 | bare except swallows real errors silently in prod | catch the specific exception"
MODE = {"body": WRONG}

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        out = json.dumps({"choices": [{"message": {"role": "assistant", "content": MODE["body"]}}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
PORT = srv.server_address[1]

tmp = tempfile.mkdtemp(prefix="ag_")
target = os.path.join(tmp, "target.py")
open(target, "w", encoding="utf-8").write("def f(x):\n    try:\n        return 1 / x\n    except Exception:\n        return 0\n")

def run_review(url):
    env = dict(os.environ, HARNESS_CLAUDE_URL=url, LATHE_REVIEW_USE_CLI="0")   # endpoint ONLY (the air-gapped niche)
    r = subprocess.run([sys.executable, HREVIEW, "correctness", target], cwd=INNER,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

fails = []
def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

rc, out = run_review("http://127.0.0.1:%d/v1/chat/completions" % PORT)
check("D5b: wrong-200 junk is REJECTED (rc!=0)", rc != 0, "rc=%d" % rc)
check("D5b: rejection is explicit (wrong-200 guard fired)", "rejected" in out and "wrong-200" in out)
check("D5b: no junk verdict written as a review", "helpful assistant" not in open(
    os.path.join(INNER, "docs", "ce", "review_correctness.txt"), encoding="utf-8", errors="replace").read())

MODE["body"] = VALID
rc2, out2 = run_review("http://127.0.0.1:%d/v1/chat/completions" % PORT)
check("sanity: a VALID review shape is ACCEPTED (rc=0)", rc2 == 0, "rc=%d out=%s" % (rc2, out2[-200:]))

rc3, out3 = run_review("http://127.0.0.1:1/v1/chat/completions")               # dead endpoint, CLI disabled
check("D5a: no usable backend -> fail LOUD (rc!=0)", rc3 != 0, "rc=%d" % rc3)
check("D5a: explicit '[review unavailable' marker", "[review unavailable" in out3)

srv.shutdown()
print("\nanalyst-guard e2e: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
