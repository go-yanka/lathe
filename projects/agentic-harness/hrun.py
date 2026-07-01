"""hrun.py — harness-run wrapper. Runs a plan through the engine AND logs the outcome to the portal's
build-activity feed (POST /api/admin/activity), so every regen shows up LIVE on /activity.html as work lands.
Hand-written dev tooling (like build_all.py / run_live.py), not product code — preserved across rebuilds.

Usage:  python hrun.py <plan_path> [model] [N]        (model default: openai:g26b, N default: 8)
"""
import subprocess, sys, re, json, os, urllib.request

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "engine_v2.py")
APP = os.environ.get("LATHE_APP", "http://127.0.0.1:5058")
PY = sys.executable


def _log(kind, title, detail, status):
    """Best-effort POST to the activity feed; never fails the run if the app is down."""
    try:
        body = json.dumps({"kind": kind, "title": title, "detail": detail, "status": status}).encode()
        req = urllib.request.Request(APP + "/api/admin/activity", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        print("(activity log skipped: %s)" % e)


def main():
    if len(sys.argv) < 2:
        print("usage: python hrun.py <plan> [model] [N]")
        return 2
    plan = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("HARNESS_MODEL", "openai:g26b")  # env-overridable default (ported from canonical 2026-06-29)
    N = sys.argv[3] if len(sys.argv) > 3 else "8"
    name = os.path.basename(plan)

    _log("build", "Building " + name, "model=" + model, "wip")
    r = subprocess.run([PY, ENGINE, plan, model, N], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    print(out)

    art = re.search(r"\[artifact (\w+)\s*\]\s*(\S+)\s*\((\d+) chars.*?functional=(\w+)\)", out)
    fm = re.search(r"functions implemented: (\d+)/(\d+)", out)
    integ = "PASS" if "integration: PASS" in out else ("FAIL" if "integration: FAIL" in out else "n/a")

    if "[artifact FAIL" in out and not art:
        _log("build", "FAILED " + name, "UI gate did not pass — analyst refines the spec", "fail")
    elif art:
        who, path, chars, func = art.groups()
        ok = (func == "yes")
        _log("build",
             ("Shipped " if ok else "FAILED ") + os.path.basename(path),
             "%s • %s • %s chars • gate functional=%s" % (name, who, chars, func),
             "ok" if ok else "fail")
    elif fm:
        solved = fm.group(1) == fm.group(2)
        ok = solved and integ != "FAIL"
        _log("build",
             ("Built " if ok else "FAILED ") + name,
             "functions %s/%s • integration=%s" % (fm.group(1), fm.group(2), integ),
             "ok" if ok else "fail")
    else:
        _log("build", "Ran " + name, integ, "info")
    return r.returncode


sys.exit(main())
