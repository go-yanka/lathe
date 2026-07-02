"""A real implementer endpoint backed by Claude Fable 5 (shells `claude -p`).

OpenAI-compatible /v1/chat/completions. The engine's generation prompt goes to Fable; Fable's output is
returned as the completion, then the engine's own extract/gate/pin logic takes over unchanged.

  python review_tests/fable_implementer.py 8089

This measures the harness pipeline + a strong implementer (Fable), NOT a cheap local model.
"""
import sys, json, subprocess, shutil
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8089
CLAUDE = shutil.which("claude")


def gen(prompt):
    p = subprocess.run([CLAUDE, "-p", "--model", "claude-fable-5"],
                       input=prompt, capture_output=True, text=True, timeout=180)
    return (p.stdout or "").strip()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._send({"status": "ok", "data": [{"id": "fable"}]})
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            prompt = json.loads(self.rfile.read(n))["messages"][-1]["content"]
        except Exception:
            prompt = ""
        try:
            content = gen(prompt)
        except Exception as e:
            content = "# fable error: %s" % e
        self._send({"choices": [{"message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": len(prompt)//4, "completion_tokens": len(content)//4}})


if __name__ == "__main__":
    if not CLAUDE:
        sys.exit("no claude CLI on PATH")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
