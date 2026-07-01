"""A7 road-ready gate tests. Deterministic ordering/short-circuit via stub stages, PLUS a LIVE
boot+health proof against a throwaway http.server (no fastapi dep, no real product server touched).
Run: python tools/test_road_ready.py"""
import os
import socket
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from road_ready import road_ready, import_stage, boot_health_stage, http_ready


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    # 1. all stages pass -> ok, every stage ran
    ran = []
    stages = [(f"s{i}", (lambda i=i: (ran.append(i) or (True, f"ok{i}")))) for i in range(3)]
    r = road_ready(stages)
    assert r["ok"] is True and r["failed"] is None and ran == [0, 1, 2], (r, ran)

    # 2. fail-closed: stage 1 fails -> stage 2 NEVER runs (short-circuit)
    ran = []
    stages = [("a", lambda: (ran.append("a") or (True, "ok"))),
              ("b", lambda: (ran.append("b") or (False, "boom"))),
              ("c", lambda: (ran.append("c") or (True, "ok")))]
    r = road_ready(stages)
    assert r["ok"] is False and r["failed"] == "b" and ran == ["a", "b"], (r, ran)

    # 3. a stage that RAISES is caught as a failure (never crashes the gate)
    r = road_ready([("x", lambda: (_ for _ in ()).throw(RuntimeError("kaboom")))])
    assert r["ok"] is False and r["failed"] == "x" and "raised" in r["results"][0]["detail"], r

    # 4. import_stage LIVE: a real importable module passes; a broken one fails
    assert import_stage("json", cwd=os.getcwd())()[0] is True
    broken = tempfile.mkdtemp()
    with open(os.path.join(broken, "brokenmod.py"), "w") as f:
        f.write("def x(:\n")   # syntax error
    assert import_stage("brokenmod", cwd=broken)()[0] is False

    # 5. boot+health LIVE: start a throwaway static server, prove it goes healthy then is torn down
    port = _free_port()
    served = tempfile.mkdtemp()
    with open(os.path.join(served, "index.html"), "w") as f:
        f.write("ok")
    cmd = [sys.executable, "-m", "http.server", str(port)]
    stage = boot_health_stage(cmd, f"http://127.0.0.1:{port}/", cwd=served, timeout=15)
    ok, detail = stage()
    assert ok is True, f"server should have booted healthy: {detail}"
    # after the stage returns, the server must be GONE (port reusable)
    ok2, _ = http_ready(f"http://127.0.0.1:{port}/", timeout=1.5)
    assert ok2 is False, "server was left running — boot_health_stage must tear it down"

    # 6. boot+health LIVE negative: a command that exits immediately never goes healthy
    port2 = _free_port()
    stage = boot_health_stage([sys.executable, "-c", "raise SystemExit(1)"],
                              f"http://127.0.0.1:{port2}/", timeout=4)
    ok, detail = stage()
    assert ok is False and ("exited" in detail or "never healthy" in detail), detail

    print("A7 road_ready: ALL 6 ASSERTIONS PASS — ordered fail-closed gate, raises caught, "
          "LIVE import + boot/health/teardown verified. No Claude calls.")


if __name__ == "__main__":
    main()
