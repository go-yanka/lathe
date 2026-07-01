"""autonomy_loop — the deterministic conductor of the self-build loop (analyst-authored CORE glue).

Composes the gated leaf pieces:
  - T3 decide_next_action  (run / plan / halt)
  - T4 build_planner_prompt (the ask to Claude when the board is empty)
  - T5 is_valid_plan        (gate Claude's response before trusting it)

All real I/O is INJECTED via `deps` (request_spec, save_plan, run_task, commit) so the control flow
is unit-testable with mocks today, and the same code runs live once the Claude call (T6, needs :8787)
and the real board/engine wiring are plugged in. The weak model is never the conductor — this is.
"""
import importlib.util
import os

_TOOLS = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    path = os.path.join(_TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


decide_next_action = _load("autonomy_controller").decide_next_action
build_planner_prompt = _load("planner_prompt").build_planner_prompt
is_valid_plan = _load("plan_validator").is_valid_plan


def run_once(tasks, objective, done_list, deps, last_blocker=None):
    """Execute ONE deterministic step of the autonomy loop and report what happened.

    deps: dict of injected callables:
      - request_spec(prompt:str) -> str        (T6: POST to the Claude proxy; returns plan text)
      - save_plan(text:str)      -> task        (persist the plan + enqueue it on the board)
      - run_task(task)           -> {'ok':bool,'reason':str}   (run the engine on the task)
      - commit(message:str)      -> None        (git checkpoint)

    Returns a dict: {'step': <what happened>, ...}.
    """
    decision = decide_next_action(tasks)
    action = decision["action"]

    if action == "halt":
        return {"step": "halt", "task": decision["task"], "reason": decision["reason"]}

    if action == "plan":
        prompt = build_planner_prompt(objective, done_list, last_blocker)
        text = deps["request_spec"](prompt)
        verdict = is_valid_plan(text)
        if not verdict["ok"]:
            return {"step": "plan_rejected", "reason": verdict["reason"]}
        task = deps["save_plan"](text)
        return {"step": "planned", "task": task}

    # action == "run"
    task = decision["task"]
    result = deps["run_task"](task)
    if result.get("ok"):
        committed = deps["commit"]("autonomy: " + str(task.get("name", "task")))
        return {"step": "ran_ok", "task": task, "committed": committed}
    return {"step": "ran_failed", "task": task, "reason": result.get("reason", "")}
