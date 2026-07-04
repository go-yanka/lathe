# H_manifest_core — operating contract PHASE 0 (issue #12): the pure DECISION core of the per-invocation
# manifest. Three load-bearing computations: (1) role-split token usage with the COMPLETENESS invariant that
# makes the analyst-token gap un-hideable (a role with calls but no tokens = uninstrumented, visibly); (2)
# imputed USD cost from a versioned pricebook (subscription $0 real vs list-price imputed); (3) the tamper-
# evident self-hash. The I/O spine (tools/manifest.py begin/finalize) is hand-maintained glue around these.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "manifest_core"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "role_usage",
     "kinds": ["edge"],
     "prompt": ("Write role_usage(roles) -> dict. `roles` maps role name -> {'p': prompt_tokens, 'e': "
                "completion_tokens, 'calls': n_calls, 'src': str}. Build: {'tokens': {'prompt': P, "
                "'completion': E, 'total': P+E, 'by_role': {role: {'prompt': p, 'completion': e, 'total': "
                "p+e, 'source': src}}, 'completeness': {'all_calls_attributed': bool, "
                "'uninstrumented_calls': U}}, 'calls': {'total': N, <role>: calls...}}. Coerce each of "
                "p/e/calls via: 0 if bool or not int/float or negative, else int(v). source = str(src) if "
                "src is a str else 'n/a'. A role is UNINSTRUMENTED when its calls > 0 but its total tokens "
                "== 0; U = sum of calls of uninstrumented roles; all_calls_attributed = (U == 0). roles not "
                "a dict -> the empty-but-complete shape (P=E=N=U=0, all_calls_attributed True, empty "
                "by_role). Skip non-str role keys and non-dict role values. Never raise." + "\n" + _ONLY),
     "tests": [
        "u = role_usage({'analyst': {'p': 100, 'e': 50, 'calls': 2, 'src': 'measured'}, 'implementer': {'p': 10, 'e': 5, 'calls': 1, 'src': 'measured'}})",
        "assert u['tokens']['prompt'] == 110 and u['tokens']['completion'] == 55 and u['tokens']['total'] == 165",
        "assert u['tokens']['by_role']['analyst'] == {'prompt': 100, 'completion': 50, 'total': 150, 'source': 'measured'}",
        "assert u['tokens']['completeness'] == {'all_calls_attributed': True, 'uninstrumented_calls': 0} and u['calls']['total'] == 3",
        "g = role_usage({'analyst': {'p': 0, 'e': 0, 'calls': 3, 'src': 'n/a'}})",
        "assert g['tokens']['completeness'] == {'all_calls_attributed': False, 'uninstrumented_calls': 3}  # the gap is VISIBLE",
        "z = role_usage(None); assert z['tokens']['total'] == 0 and z['tokens']['completeness']['all_calls_attributed'] is True and z['calls']['total'] == 0",
        "b = role_usage({'x': {'p': True, 'e': -5, 'calls': 'bad', 'src': None}}); assert b['tokens']['by_role']['x'] == {'prompt': 0, 'completion': 0, 'total': 0, 'source': 'n/a'}",
     ]},
    {"name": "imputed_cost",
     "kinds": ["edge"],
     "prompt": ("Write imputed_cost(roles, prices) -> dict. `roles` maps role -> {'p': prompt_tokens, 'e': "
                "completion_tokens} (coerce like: 0 if bool/negative/non-numeric else int). `prices` maps "
                "role -> {'in_per_mtok': float, 'out_per_mtok': float} (list price per 1M tokens). Per role: "
                "cost = round(p/1e6*in_per_mtok + e/1e6*out_per_mtok, 6); role missing from prices (or "
                "prices not a dict, or bad price values) -> 0.0. Return {'imputed_by_role': {role: cost}, "
                "'imputed_total': round(sum, 6)}. roles not a dict -> {'imputed_by_role': {}, "
                "'imputed_total': 0.0}. Never raise." + "\n" + _ONLY),
     "tests": [
        "c = imputed_cost({'analyst': {'p': 1000000, 'e': 1000000}}, {'analyst': {'in_per_mtok': 3.0, 'out_per_mtok': 15.0}})",
        "assert c['imputed_by_role']['analyst'] == 18.0 and c['imputed_total'] == 18.0",
        "c2 = imputed_cost({'a': {'p': 4120, 'e': 2310}}, {'a': {'in_per_mtok': 3.0, 'out_per_mtok': 15.0}})",
        "assert abs(c2['imputed_by_role']['a'] - 0.04701) < 1e-9",
        "assert imputed_cost({'a': {'p': 100, 'e': 100}}, {})['imputed_by_role']['a'] == 0.0",
        "assert imputed_cost(None, None) == {'imputed_by_role': {}, 'imputed_total': 0.0}",
        "assert imputed_cost({'a': {'p': 100, 'e': 100}}, {'a': {'in_per_mtok': 'x', 'out_per_mtok': None}})['imputed_by_role']['a'] == 0.0",
        "m = imputed_cost({'a': {'p': 500000, 'e': 0}, 'b': {'p': 0, 'e': 200000}}, {'a': {'in_per_mtok': 5.0, 'out_per_mtok': 25.0}, 'b': {'in_per_mtok': 1.0, 'out_per_mtok': 5.0}})",
        "assert m['imputed_by_role'] == {'a': 2.5, 'b': 1.0} and m['imputed_total'] == 3.5",
     ]},
    {"name": "manifest_hash",
     "kinds": ["edge"],
     "prompt": ("Write manifest_hash(manifest) -> str, the tamper-evident self-hash of a manifest dict. "
                "Rules: manifest not a dict -> ''. Deep-copy the input (must NOT mutate it). In the copy, if "
                "'integrity' is a dict, set copy['integrity']['manifest_sha256'] = '' (blank the self-hash "
                "field). Serialize the copy with json.dumps(copy, sort_keys=True, separators=(',', ':'), "
                "default=str) and return 'sha256:' + hashlib.sha256(serialized.encode('utf-8')).hexdigest(). "
                "Never raise (any error -> '')." + "\n" + _ONLY),
     "tests": [
        "m = {'a': 1, 'integrity': {'manifest_sha256': 'sha256:OLD', 'partial': False}}",
        "h1 = manifest_hash(m)",
        "assert h1.startswith('sha256:') and len(h1) == 71",
        "assert m['integrity']['manifest_sha256'] == 'sha256:OLD'  # input NOT mutated",
        "assert manifest_hash({'a': 1, 'integrity': {'manifest_sha256': 'DIFFERENT', 'partial': False}}) == h1  # self-hash field excluded",
        "assert manifest_hash({'a': 1, 'integrity': {'manifest_sha256': '', 'partial': True}}) != h1  # other fields DO count",
        "assert manifest_hash({'b': 2, 'integrity': {'manifest_sha256': '', 'partial': False}}) != h1",
        "assert manifest_hash('nope') == '' and manifest_hash(None) == ''",
        "assert manifest_hash({'x': 1}) == manifest_hash({'x': 1})  # deterministic",
     ]},
]

CRITERIA = [
    {"id": "C1", "text": "Role-split usage with the completeness invariant: uninstrumented calls are visible, never silent zeros (#12 T4)",
     "tests": ["role_usage"]},
    {"id": "C2", "text": "Imputed USD cost per role from a versioned pricebook (subscription $0 real vs list imputed) (#12 T5)",
     "tests": ["imputed_cost"]},
    {"id": "C3", "text": "Tamper-evident deterministic self-hash (integrity field blanked, input unmutated) (#12 T8)",
     "tests": ["manifest_hash"]},
]
