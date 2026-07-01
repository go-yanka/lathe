"""cassette_proxy — deterministic record/replay for model calls in gates (LLM-pipeline e2e gating).

The problem (a downstream project, 2026-06-30): a correctness invariant that only breaks at scale (e.g. each distilled
gist maps to the RIGHT source paragraph across many model batches) can only be exercised by an end-to-end run of
the REAL pipeline — which is slow (~1-2 min) and NONDETERMINISTIC (model output varies), so it can't be a build
gate. Real scale bugs then ship past green builds (a gist<->paragraph off-by-one did exactly this).

This is an OpenAI-compatible passthrough proxy that RECORDS {request-hash -> response} on first run and REPLAYS
by hash after — so an INTEGRATION/functional gate can drive the real pipeline offline, deterministically, in
milliseconds, every build. Point your pipeline's model base URL at this proxy; check the cassette in beside the
plan; refresh with LATHE_GATE_RECORD=1 when the prompt/pipeline changes.

  # record (first time, or after a prompt change): forward to the real endpoint + capture
  LATHE_GATE_RECORD=1 LATHE_CASSETTE=plans/summarize.cassette.json \
      LATHE_CASSETTE_UPSTREAM=http://127.0.0.1:8090 python tools/cassette_proxy.py
  # replay (every build): serve recorded responses by hash, no network, no variance
  LATHE_CASSETTE=plans/summarize.cassette.json python tools/cassette_proxy.py
  # then point the pipeline at it:  MODEL_BASE_URL=http://127.0.0.1:8791/v1  (or whatever your code reads)

Env: LATHE_CASSETTE (json path, required), LATHE_CASSETTE_UPSTREAM (real endpoint for record/miss),
     LATHE_GATE_RECORD (1 = always forward+save), LATHE_CASSETTE_PORT (default 8791),
     LATHE_CASSETTE_STRICT (1 = a replay miss is a hard 409 error, so an incomplete cassette FAILS the gate
     loudly instead of silently hitting the network — recommended for CI once recorded).
Minimal cut: non-streaming JSON chat/completions. Streaming + fixture convention are follow-ups.
"""
import hashlib
import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CASSETTE = os.environ.get("LATHE_CASSETTE", "cassette.json")
UPSTREAM = os.environ.get("LATHE_CASSETTE_UPSTREAM", "").rstrip("/")
RECORD = os.environ.get("LATHE_GATE_RECORD") == "1"
STRICT = os.environ.get("LATHE_CASSETTE_STRICT") == "1"
PORT = int(os.environ.get("LATHE_CASSETTE_PORT", "8791"))


def _load():
    try:
        with open(CASSETTE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:      # a corrupt cassette must NOT silently become empty (that would
        sys.exit("cassette_proxy: %s unreadable: %s" % (CASSETTE, e))   # re-record everything / mask staleness)


def _save(store):
    tmp = CASSETTE + ".tmp"                            # atomic: a crash mid-write can't truncate the cassette
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=0, sort_keys=True)
    os.replace(tmp, CASSETTE)


def _key(path, body_bytes):
    """Stable hash of the logical request: METHOD path + canonical JSON body (sorted keys). Same request every
    run -> same key -> same recorded response. A prompt/param change changes the key (so you re-record)."""
    try:
        canon = json.dumps(json.loads(body_bytes.decode("utf-8")), sort_keys=True, separators=(",", ":"))
    except Exception:
        canon = body_bytes.decode("utf-8", "replace")
    return hashlib.sha256((path + "\n" + canon).encode("utf-8")).hexdigest()


_store = _load()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                          # quiet; we print our own record/replay lines

    def _reply(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        key = _key(self.path, body)
        if not RECORD and key in _store:
            print("  [cassette REPLAY %s %s]" % (self.path, key[:12]))
            self._reply(200, _store[key])
            return
        if not RECORD and STRICT:                     # replay miss under STRICT = the cassette is stale/incomplete
            print("  [cassette MISS (strict) %s %s -> 409]" % (self.path, key[:12]))
            self._reply(409, {"error": "cassette miss: no recorded response for this request; re-record with "
                                       "LATHE_GATE_RECORD=1", "key": key})
            return
        if not UPSTREAM:
            self._reply(502, {"error": "cassette miss and no LATHE_CASSETTE_UPSTREAM to record from", "key": key})
            return
        try:                                          # record (or non-strict replay miss): forward + capture
            req = urllib.request.Request(UPSTREAM + self.path, data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=int(os.environ.get("LATHE_CASSETTE_TIMEOUT", "300"))) as r:
                resp = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            self._reply(502, {"error": "upstream failed: %s" % e, "key": key})
            return
        _store[key] = resp
        _save(_store)
        print("  [cassette %s %s %s]" % ("RECORD" if RECORD else "record-on-miss", self.path, key[:12]))
        self._reply(200, resp)


if __name__ == "__main__":
    mode = "RECORD (forward+save all)" if RECORD else ("REPLAY strict" if STRICT else "REPLAY (record-on-miss)")
    print("cassette_proxy on :%d  cassette=%s  upstream=%s  mode=%s  (%d entries)"
          % (PORT, CASSETTE, UPSTREAM or "(none)", mode, len(_store)))
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
