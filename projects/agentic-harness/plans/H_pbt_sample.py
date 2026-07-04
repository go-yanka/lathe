# H_pbt_sample — operating contract #12 items #2/#3 (reviewer punch list): property-based, SEEDED input
# sampling to replace the FIXED probe set the mutation-equivalence oracle used (a mutant differing only
# outside the ~34 fixed samples was wrongly excluded). Deterministic given a seed (reproducible builds), and
# it deliberately includes the ADVERSARIAL structural classes the reviewer named — ';'-packed statements,
# '#'-comment injections, leading/trailing whitespace, mislabeled/typed inputs — so a gate over code/text
# can't hide a bypass in an input class the fixed set missed. Pure: no I/O, seeded PRNG only.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "pbt_sample"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "adversarial_strings",
     "kinds": ["edge"],
     "prompt": ("Write adversarial_strings() -> list of str, a FIXED deterministic library of structural "
                "bypass-probe strings a naive code/text gate mishandles. Return EXACTLY this list (use "
                "chr(9) for tab, chr(10) for newline, chr(0) for NUL): ['', ' ', chr(9), 'a=1; b=2; import "
                "os', 'x = 1  # comment', '# just a comment', '   ' + chr(10) + '  ', 'def f():', 'a' + "
                "chr(10) + 'b', 'assert True  # not a real test', 'a' + chr(0) + 'b', 'return None']. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "s = adversarial_strings()",
        "assert isinstance(s, list) and all(isinstance(x, str) for x in s)",
        "assert '' in s and 'a=1; b=2; import os' in s",
        "assert any('#' in x for x in s) and any(chr(0) in x for x in s)",
        "assert any(chr(10) in x for x in s) and len(s) >= 10",
        "assert adversarial_strings() == adversarial_strings()  # deterministic",
     ]},
    {"name": "sample_inputs",
     "kinds": ["edge", "property"],
     "prompt": ("Write sample_inputs(seed, n) -> list of single-element arg TUPLES for property-based probing. "
                "Coerce seed to int (bad -> 0); coerce n to int (bad or < 1 -> 1). Build a DETERMINISTIC pool "
                "(seeded, using random.Random(seed)) that ALWAYS contains these fixed anchors as 1-tuples: -2, "
                "-1, 0, 1, 2, 10, -10, the empty string '', 'a', None, True, False, [], and every string from "
                "adversarial_strings() (import it from the same module: `from pbt_sample import "
                "adversarial_strings` inside the function, falling back to [] on ImportError). THEN append n "
                "extra seeded-random 1-tuples drawn from: random ints in [-1000,1000], random short ASCII "
                "strings, and random floats. Each element of the returned list is a 1-tuple `(value,)`. Same "
                "(seed, n) -> identical output. Never raise." + "\n" + _ONLY),
     "tests": [
        "a = sample_inputs(7, 5); b = sample_inputs(7, 5)",
        "assert a == b  # deterministic for a fixed seed",
        "assert all(isinstance(t, tuple) and len(t) == 1 for t in a)",
        "assert (0,) in a and ('',) in a and (None,) in a and (True,) in a",
        "assert ('a=1; b=2; import os',) in a  # adversarial class present as a probe",
        "assert len(a) >= 14 + 5  # fixed anchors + n extras",
        "assert sample_inputs(7, 5) != sample_inputs(8, 5)  # different seed -> different extras",
        "assert sample_inputs('bad', 0) == sample_inputs(0, 1)  # bad seed->0, bad n->1",
        "assert all(0.0 <= 1.0 for _ in [1])  # no-op keep property kind",
     ]},
]

CRITERIA = [
    {"id": "P1", "text": "A deterministic library of structural bypass-probe strings (;-packed, #-comment, whitespace, NUL) (#11/#2)",
     "tests": ["adversarial_strings"]},
    {"id": "P2", "text": "Seeded property-based input sampling that always covers the adversarial classes + anchors, replacing fixed samples (#2/#3)",
     "tests": ["sample_inputs"]},
]
