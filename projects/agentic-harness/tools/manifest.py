# hand-maintained SPINE (operating contract #12 Phase 0) — the per-invocation manifest emitter. I/O glue
# ONLY: the decision logic (completeness invariant, cost math, self-hash) is pinned in manifest_core.py
# (harness-built, STRICT). This class is bound in lathe.py main() ABOVE the skill layer: begin() writes a
# partial:true stub immediately (atomic), finalize() runs in a `finally` so no return/raise/SystemExit/
# SIGINT inside a handler can skip emission. Skills/workflows can only APPEND content; they have no handle
# to suppress the record. Schema 1.0.0 — every field present on every emission (nulls, not omissions).
import json
import os
import time

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_TOOLS)))       # repo root

SCHEMA_VERSION = "1.0.0"
EMITTER_VERSION = "1.0.0"


def _core():
    import sys
    if _TOOLS not in sys.path:
        sys.path.insert(0, _TOOLS)
    import manifest_core
    return manifest_core


def _atomic_write(path, content):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def out_dir():
    return os.path.join(_ROOT, "docs", "ce")


def _skeleton(run_id, argv, command, routed_via):
    """Every group present from the first write (T3 structural completeness)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": "cem_" + run_id,
        "run_id": run_id,
        "parent_run_id": None,
        "invocation": {
            "argv": list(argv or []), "command": command, "routed_via": routed_via,
            "is_bare_goal": routed_via == "bare-goal",
            "cwd": os.getcwd(), "pid": os.getpid(), "invoked_by": "cli",
            "lathe_version": _version(), "strict": os.environ.get("LATHE_STRICT") == "1",
            "env_snapshot": {k: os.environ[k] for k in
                             ("LATHE_STRICT", "LATHE_MODEL", "LATHE_TRIES", "LATHE_THINK") if k in os.environ},
        },
        "intake": {"invocation_type": command, "goal": None, "run_started_at":
                   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        "front_end": {"ran": False, "clarify": None, "assumptions": []},
        "selection": {"selector": None, "personas": [], "lenses": []},
        "contributors": [],
        "work": {"steps": []},
        "gates": {"all_pass": None, "verdicts": []},
        "models": [],
        "usage": None,
        "timing": {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "ended_at": None, "elapsed_s": None},
        "outcome": {"status": None, "reason": None, "exit_code": None, "refused": False,
                    "error": None, "artifacts": [], "pins": []},
        "integrity": {"emitted_by": "dispatcher.finalize", "emitter_version": EMITTER_VERSION,
                      "manifest_sha256": "", "partial": True},
    }


def _version():
    try:
        return open(os.path.join(_ROOT, "VERSION"), encoding="utf-8").read().strip()
    except Exception:
        return "unknown"


class Manifest:
    """One instance per CLI invocation. All methods best-effort: recording must never break the run."""

    def __init__(self, data, t0):
        self._d = data
        self._t0 = t0
        self._roles = {}          # role -> {p,e,calls,src}; fed by the engine via record_usage
        self._role_prices = {}    # role -> {in_per_mtok,out_per_mtok}
        self._finalized = False

    _seq = 0

    @classmethod
    def begin(cls, argv, command, routed_via):
        cls._seq += 1        # same-second invocations in one process must not collide on run_id
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + ("%04x" % (os.getpid() & 0xFFFF)) + "-%02d" % cls._seq
        m = cls(_skeleton(run_id, argv, command, routed_via), time.time())
        try:                                   # partial stub on disk NOW: a hard-kill leaves evidence
            os.makedirs(out_dir(), exist_ok=True)
            _atomic_write(m.json_path(), json.dumps(m._d, indent=1, default=str))
        except Exception:
            pass
        return m

    def json_path(self):
        return os.path.join(out_dir(), self._d["run_id"] + ".manifest.json")

    def md_path(self):
        return os.path.join(out_dir(), self._d["run_id"] + ".manifest.md")

    # ---- appenders (skills/engine feed content; they cannot suppress emission) ----
    def set_goal(self, goal):
        try:
            self._d["intake"]["goal"] = str(goal)
        except Exception:
            pass

    def append_contributor(self, row):
        try:
            if isinstance(row, dict):
                self._d["contributors"].append(row)
        except Exception:
            pass

    def record_gate(self, gate, verdict, blocking=True, detail=""):
        try:
            self._d["gates"]["verdicts"].append({"gate": str(gate), "verdict": str(verdict),
                                                 "blocking": bool(blocking), "detail": str(detail)})
        except Exception:
            pass

    def set_selection(self, selector, personas, lenses):
        try:
            self._d["selection"] = {"selector": selector, "personas": list(personas or []),
                                    "lenses": list(lenses or [])}
        except Exception:
            pass

    def record_usage(self, role, p, e, calls, src, price=None):
        """Engine feeds per-role token usage here (L2/L3). Cumulative."""
        try:
            b = self._roles.setdefault(str(role), {"p": 0, "e": 0, "calls": 0, "src": "n/a"})
            b["p"] += int(p or 0); b["e"] += int(e or 0); b["calls"] += int(calls or 0)
            if src:
                b["src"] = str(src)
            if isinstance(price, dict):
                self._role_prices[str(role)] = price
        except Exception:
            pass

    def add_model(self, row):
        try:
            if isinstance(row, dict):
                self._d["models"].append(row)
        except Exception:
            pass

    def set_outcome(self, status, exit_code, reason=None, error=None, artifacts=None, pins=None):
        try:
            self._d["outcome"] = {"status": status, "reason": reason, "exit_code": exit_code,
                                  "refused": status == "refuse", "error": error,
                                  "artifacts": list(artifacts or []), "pins": list(pins or [])}
        except Exception:
            pass

    # ---- the un-skippable emitter ----
    def finalize(self):
        """ALWAYS writes docs/ce/<run_id>.manifest.{json,md}. Idempotent; never raises."""
        if self._finalized:
            return
        self._finalized = True
        try:
            core = _core()
            usage = core.role_usage(self._roles)
            try:
                from pricebook import PRICEBOOK_VERSION
            except Exception:
                PRICEBOOK_VERSION = "unknown"
            cost = core.imputed_cost(self._roles, self._role_prices)
            usage["cost_usd"] = {"total": 0.0, "imputed_total": cost["imputed_total"],
                                 "imputed_by_role": cost["imputed_by_role"]}
            usage["pricebook_version"] = PRICEBOOK_VERSION
            self._d["usage"] = usage
            self._d["timing"]["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._d["timing"]["elapsed_s"] = round(time.time() - self._t0, 1)
            v = self._d["gates"]["verdicts"]
            self._d["gates"]["all_pass"] = (all(x.get("verdict") == "pass" for x in v) if v else None)
            if self._d["outcome"]["status"] is None:      # finalize reached without an outcome = crash-partial
                self._d["outcome"]["status"] = "error"
                self._d["outcome"]["error"] = "no outcome recorded before finalize"
            self._d["integrity"]["partial"] = False
            self._d["integrity"]["manifest_sha256"] = core.manifest_hash(self._d)
            os.makedirs(out_dir(), exist_ok=True)
            _atomic_write(self.json_path(), json.dumps(self._d, indent=1, default=str))
            _atomic_write(self.md_path(), render(self._d))
        except Exception as e:
            # last-resort partial record — an invisible failure to record is the one unacceptable outcome
            try:
                import sys
                sys.stderr.write("manifest finalize degraded: %r\n" % (e,))
                self._d["integrity"]["partial"] = True
                os.makedirs(out_dir(), exist_ok=True)
                _atomic_write(self.json_path(), json.dumps(self._d, indent=1, default=str))
            except Exception:
                pass


def render(d):
    """Deterministic human render, fixed section order; phases not reached print 'not reached'."""
    try:
        out = d.get("outcome", {}) or {}
        status = (out.get("status") or "partial").upper()
        L = ["LATHE RUN MANIFEST - %s%s%s" % (d.get("run_id", "?"), " " * 8, status),
             "-" * 72,
             "INTAKE     %s %s" % (d.get("invocation", {}).get("command", "?"),
                                   json.dumps((d.get("invocation", {}).get("argv") or [])[1:])[:80]),
             "           routed=%s  strict=%s  lathe %s" % (
                 d.get("invocation", {}).get("routed_via"), d.get("invocation", {}).get("strict"),
                 d.get("invocation", {}).get("lathe_version"))]
        goal = (d.get("intake") or {}).get("goal")
        L.append("GOAL       %s" % (goal if goal else "- not recorded -"))
        pers = (d.get("selection") or {}).get("personas") or []
        L.append("SELECTION  %s" % (", ".join(str(p.get("id", p)) if isinstance(p, dict) else str(p)
                                              for p in pers) if pers else "- not reached -"))
        cons = d.get("contributors") or []
        L.append("CONTRIBUTORS")
        if cons:
            for c in cons:
                L.append("  %-12s %s" % (c.get("id", "?"), c.get("action", "")))
        else:
            L.append("  - none recorded -")
        gv = (d.get("gates") or {}).get("verdicts") or []
        L.append("GATES      " + ("  ".join("%s %s" % (g.get("gate"), "PASS" if g.get("verdict") == "pass"
                                                       else str(g.get("verdict")).upper()) for g in gv)
                                  if gv else "- not reached -"))
        u = d.get("usage") or {}
        t = (u.get("tokens") or {})
        comp = (t.get("completeness") or {})
        L.append("USAGE      tokens %s  attribution: %s  imputed $%s  (pricebook %s)" % (
            t.get("total", 0), "COMPLETE" if comp.get("all_calls_attributed") else
            "INCOMPLETE (%s uninstrumented)" % comp.get("uninstrumented_calls", "?"),
            (u.get("cost_usd") or {}).get("imputed_total", 0.0), u.get("pricebook_version", "?")))
        L.append("TIMING     %ss" % ((d.get("timing") or {}).get("elapsed_s"),))
        L.append("OUTCOME    %s - %s (exit %s)" % (status, out.get("reason") or out.get("error") or "",
                                                   out.get("exit_code")))
        L.append("-" * 72)
        L.append("manifest %s - emitter %s" % ((d.get("integrity") or {}).get("manifest_sha256", "")[:23],
                                               (d.get("integrity") or {}).get("emitter_version")))
        return "\n".join(L) + "\n"
    except Exception:
        return "MANIFEST RENDER FAILED\n"
