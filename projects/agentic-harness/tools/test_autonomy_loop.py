import importlib.util, os
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
run_once = load("autonomy_loop","tools/autonomy_loop.py").run_once

VALID_PLAN = "OUT_DIR=... MODULE_NAME=... FUNCTIONS=[...] tests=[...]"
committed = []
def deps(plan_text=VALID_PLAN, run_ok=True):
    return {
        "request_spec": lambda prompt: plan_text,
        "save_plan":    lambda text: {"name":"new_task","status":"pending"},
        "run_task":     lambda task: {"ok": run_ok, "reason": "" if run_ok else "gate failed"},
        "commit":       lambda msg: committed.append(msg),
    }

results=[]
# 1. empty board -> the loop asks Claude, gets a valid plan -> planned
r=run_once([], "build the thing", [], deps()); results.append(("empty->planned", r["step"]=="planned" and r["task"]["status"]=="pending"))
# 2. empty board, Claude returns garbage -> plan_rejected (gate protects us)
r=run_once([], "x", [], deps(plan_text="I cannot help with that")); results.append(("garbage->plan_rejected", r["step"]=="plan_rejected"))
# 3. pending task -> runs it, succeeds, commits
committed.clear()
r=run_once([{"name":"T1","status":"pending"}], "x", [], deps(run_ok=True)); results.append(("pending->ran_ok+commit", r["step"]=="ran_ok" and committed==["autonomy: T1"]))
# 4. pending task that fails the gate -> ran_failed, NO commit
committed.clear()
r=run_once([{"name":"T1","status":"pending"}], "x", [], deps(run_ok=False)); results.append(("fail->ran_failed,no commit", r["step"]=="ran_failed" and committed==[]))
# 5. blocked only -> halt
r=run_once([{"name":"T1","status":"blocked"}], "x", [], deps()); results.append(("blocked->halt", r["step"]=="halt"))
# 6. all done -> plan again (self-feeds)
r=run_once([{"name":"T1","status":"done"}], "x", ["T1"], deps()); results.append(("all-done->planned", r["step"]=="planned"))

ok=sum(1 for _,v in results if v)
for n,v in results: print(("PASS " if v else "FAIL ")+n)
print(f"=== {ok}/{len(results)} loop branches correct ===")
