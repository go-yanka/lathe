"""model_profiles.py — per-model-class DRAFTING STANDARDS (hand-authored CORE_INFRA data; owner design).

The analyst drafts specs FOR the implementer in use: a frontier model gets whole-file latitude; a small
local model gets decomposition, worked examples, explicit-import rules and skeletons. `profile_for(model)`
returns the standard the drafter/repairer injects into the analyst prompt, keyed by the harness-built
classifier (tools/model_class.py: frontier | local-large | local-small).

These are the saved, reusable "standards for each kind of model" — tune them here, every draft and repair
picks the change up immediately. Never model-written (a plan overwriting this would steer its own specs).
"""

PROFILES = {
    "frontier": {
        "artifact_model": "claude",          # webapp lane: whole-file generation by the capable model
        "artifact_skeleton": False,          # no scaffold needed — it can carry a whole file
        "directives": (
            "IMPLEMENTER PROFILE: frontier-class (capable). Whole files and multi-step functions are fine. "
            "Prefer fewer, richer units. Tests still pin behaviour exactly (>=4 per function)."
        ),
    },
    "local-large": {
        "artifact_model": "local",
        "artifact_skeleton": False,
        "directives": (
            "IMPLEMENTER PROFILE: local-large (30B+ class). Moderate complexity per unit is fine, but "
            "prefer single-responsibility functions over multi-step ones; give ONE worked input->output "
            "example per function; state edge-cases explicitly (None, empty, bounds)."
        ),
    },
    "local-small": {
        "artifact_model": "local",
        "artifact_skeleton": True,           # webapp lane: analyst writes the scaffold, model fills ONE region
        "directives": (
            "IMPLEMENTER PROFILE: local-small (<=13B class). HARD RULES for this implementer:\n"
            "  - every function must be a SIMPLE single-pass transform a junior could write in minutes;\n"
            "  - NO graph/BFS/recursion/parsing/state machines - move any hard logic into HEADER yourself\n"
            "    and leave only a thin wrapper to fill;\n"
            "  - every prompt gives ONE WORKED EXAMPLE of exact input -> output;\n"
            "  - any import must be stated: 'put `import X` as the FIRST line INSIDE the function body';\n"
            "  - for a whole-file ARTIFACT: do NOT ask it for the whole file. YOU write the complete working\n"
            "    scaffold in a \"skeleton\" field (page shell + event wiring + the run loop) with exactly ONE\n"
            "    __FILL__ marker for a BOUNDED data/config region (shapes, constants, lookup tables)."
        ),
    },
}


def profile_for(model):
    """The drafting standard for a model string. Falls back to local-small (the safe assumption)."""
    try:
        import importlib.util
        import os
        _p = importlib.util.spec_from_file_location("model_class", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "model_class.py"))
        _m = importlib.util.module_from_spec(_p); _p.loader.exec_module(_m)
        cls = _m.model_class(model)
    except Exception:
        cls = "local-small"
    prof = dict(PROFILES.get(cls, PROFILES["local-small"]))
    prof["class"] = cls
    return prof
