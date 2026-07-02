# H_sdlc — #41: the SDLC authoring layer's enforcement core. The proven template (a real product shipped
# with it): layered, ID-traced requirements UC (business use case) -> BR (business requirement) -> FR
# (functional requirement) -> TS (technical spec), every item with a stable ID and an explicit traces_to
# parent, verified top-down AND bottom-up (no orphans, no dangling refs). This is the RTM gate; the
# `lathe sdlc` spine has the analyst author the layers and REFUSES to write documents that fail it.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "sdlc_rtm"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "rtm_gaps",
     "prompt": ("Write rtm_gaps(layers) -> list of problem strings (empty = the requirements set is traceable). "
                "layers is a dict with keys 'UC','BR','FR','TS' (missing/None keys = empty lists), each a list of "
                "dicts {'id': str, 'text': str, 'traces_to': list-of-parent-id-strings} ('traces_to' is ignored "
                "for UC). Checks, reporting EVERY violation: (1) every item needs a non-empty string id and "
                "non-empty string text -> \"<LAYER>: item missing id/text\"; (2) ids must be unique ACROSS all "
                "layers -> \"duplicate id '<id>'\"; (3) every BR must have traces_to with >=1 entry and every "
                "entry must be an existing UC id -> \"<id>: traces to unknown/wrong-layer '<ref>'\" or \"<id>: "
                "traces to nothing\"; same rule FR->BR and TS->FR; (4) bottom-up coverage: every UC must be "
                "traced BY >=1 BR -> \"<id>: no BR covers this use case\"; every BR by >=1 FR -> \"<id>: no FR "
                "covers this requirement\"; every FR by >=1 TS -> \"<id>: no TS implements this requirement\". "
                "layers None/non-dict -> ['no layers']. Never raise." + "\n" + _ONLY),
     "tests": [
        "ok = {'UC':[{'id':'UC-1','text':'u'}],'BR':[{'id':'BR-1','text':'b','traces_to':['UC-1']}],'FR':[{'id':'FR-1','text':'f','traces_to':['BR-1']}],'TS':[{'id':'TS-1','text':'t','traces_to':['FR-1']}]}; assert rtm_gaps(ok) == []",
        "g = rtm_gaps({'UC':[{'id':'UC-1','text':'u'}],'BR':[{'id':'BR-1','text':'b','traces_to':[]}],'FR':[],'TS':[]}); assert any('traces to nothing' in x for x in g)",
        "g = rtm_gaps({'UC':[{'id':'UC-1','text':'u'}],'BR':[{'id':'BR-1','text':'b','traces_to':['UC-9']}],'FR':[],'TS':[]}); assert any('unknown' in x for x in g)",
        "g = rtm_gaps({'UC':[{'id':'UC-1','text':'u'}],'BR':[],'FR':[],'TS':[]}); assert any('no BR covers' in x for x in g)",
        "g = rtm_gaps({'UC':[{'id':'X','text':'u'}],'BR':[{'id':'X','text':'b','traces_to':['X']}],'FR':[],'TS':[]}); assert any('duplicate' in x for x in g)",
        "g = rtm_gaps({'UC':[{'id':'UC-1','text':''}],'BR':[],'FR':[],'TS':[]}); assert any('missing id/text' in x for x in g)",
        "g = rtm_gaps({'UC':[{'id':'UC-1','text':'u'}],'BR':[{'id':'BR-1','text':'b','traces_to':['UC-1']}],'FR':[{'id':'FR-1','text':'f','traces_to':['UC-1']}],'TS':[]}); assert any('wrong-layer' in x or 'unknown' in x for x in g)",
        "assert rtm_gaps(None) == ['no layers']",
        "g = rtm_gaps({'UC':[{'id':'UC-1','text':'u'}],'BR':[{'id':'BR-1','text':'b','traces_to':['UC-1']}],'FR':[{'id':'FR-1','text':'f','traces_to':['BR-1']}],'TS':[]}); assert any('no TS implements' in x for x in g)",
     ]},
]
