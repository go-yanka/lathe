# H_persona_manifest — persona redesign STAGE 5 (issue #9): the per-run MANIFEST (BR-6), the trust payload.
# One durable record per run: the goal, every persona CONSIDERED (with grade + pick/skip reason), which were
# SELECTED, and which CONTRIBUTED at least one verified finding — so a user can audit who was in the room and
# why. Pairs with the pin-provenance so build AND review are auditable end to end.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_manifest"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "build_manifest",
     "kinds": ["edge"],
     "prompt": ("Write build_manifest(goal, considered, selected, contributions) -> dict. Normalize into: "
                "{'goal': str(goal) if goal is not None else '', 'considered': [rows], 'selected': [names], "
                "'contributions': {name:int}, 'summary': {'considered':C,'selected':S,'contributed':K}}. "
                "Each row in `considered` (a list of dicts; skip non-dicts) becomes {'name': str(d.get('name','"
                "')), 'grade': float(d.get('grade',0.0)) (bad->0.0), 'picked': bool(d.get('picked')), 'reason': "
                "str(d.get('reason',''))}. `selected` -> list of the str items (skip non-str). `contributions` "
                "(a dict name->count) -> {str(k): int(v) for numeric v>=0}. summary: C=len(considered rows), "
                "S=len(selected), K=number of contributions whose count>0. Inputs of the wrong type -> empty "
                "equivalents. Never raise." + "\n" + _ONLY),
     "tests": [
        "m = build_manifest('fix auth', [{'name':'sec','grade':0.8,'picked':True,'reason':'top grade'}], ['sec'], {'sec':2})",
        "assert m['goal']=='fix auth' and m['considered'][0]=={'name':'sec','grade':0.8,'picked':True,'reason':'top grade'}",
        "assert m['selected']==['sec'] and m['contributions']=={'sec':2}",
        "assert m['summary']=={'considered':1,'selected':1,'contributed':1}",
        "z = build_manifest(None, None, None, None); assert z['goal']=='' and z['considered']==[] and z['summary']=={'considered':0,'selected':0,'contributed':0}",
        "assert build_manifest('g', [{'name':'x','grade':'bad'}], [], {'x':0})['considered'][0]['grade']==0.0",
        "assert build_manifest('g', [], [], {'a':3,'b':0})['summary']['contributed']==1",
     ]},
    {"name": "render_manifest",
     "kinds": ["edge"],
     "prompt": ("Write render_manifest(manifest) -> str, a human-readable markdown render of a manifest dict "
                "from build_manifest. manifest not a dict -> ''. Produce: a '# Persona run manifest' header; a "
                "'> goal: <goal>' line; a '## Considered' section with a markdown table (columns: persona | "
                "grade | picked | reason) one row per considered entry (picked shown as 'yes'/'no'); a "
                "'## Selected' line listing the selected names comma-joined; and a '## Contributions' section "
                "listing 'name: count' for each contribution. Use manifest.get(...) with safe defaults. Never "
                "raise; on any error return ''." + "\n" + _ONLY),
     "tests": [
        "m = build_manifest('fix auth', [{'name':'sec','grade':0.8,'picked':True,'reason':'top'}], ['sec'], {'sec':2})",
        "s = render_manifest(m)",
        "assert '# Persona run manifest' in s and 'fix auth' in s",
        "assert 'sec' in s and 'top' in s and '## Selected' in s",
        "assert render_manifest('nope') == '' and render_manifest(None) == ''",
        "assert '| persona | grade | picked | reason |' in render_manifest(m)",
     ]},
]

CRITERIA = [
    {"id": "R1", "text": "Assemble a normalized per-run manifest: considered+grade+reason, selected, contributions (BR-6)",
     "tests": ["build_manifest"]},
    {"id": "R2", "text": "Render the manifest as an auditable human-readable report", "tests": ["render_manifest"]},
]
