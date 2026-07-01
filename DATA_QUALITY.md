# Data-Quality Gates — catching "unit-green but wrong on real data"

Unit tests prove a function is correct on the inputs you thought of. They do **not** prove your pipeline
produced *good output on the real corpus* — a scorer that returns the same value for everything, a join that
drops half the rows, a derived table that never got repopulated. That class of bug passes every unit gate and
ships. (This is the your-product enhancement cluster, and the external review's "test verifies the contract is met,
not that it's good.")

Lathe ships **reusable, harness-built primitives** for this, plus a **convention** for wiring them as a gate.

## The primitives (pure, harness-built, in `tools/`)

| Primitive | Catches | Example |
|---|---|---|
| `distribution_anomalies(values, dominance=0.9)` | degenerate output — empty, all-identical (collapse), one value dominating | a scorer that returns 0.5 for every row |
| `dangling_references(used_ids, valid_ids)` | referential integrity — foreign keys / refs with no target (orphans) | job rows pointing at a company id that isn't in the company table |
| `incomplete_records(records, required_fields)` | corpus completeness — records missing a required field (never populated) | half the postings have no `parsed_skills` because the parser never ran on them |

Each returns a concrete list of the offenders (values / ids / indexes), so a failing gate tells you *exactly*
what's wrong, not just that something is.

## The convention: wire a data-quality gate

A project drops a `qa/data_gates.py` that loads its **real** data/output and asserts on it using the
primitives, then adds it to `run_gates.py` (so it runs on every build) or calls it from `lathe verify`:

```python
# projects/<you>/qa/data_gates.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agentic-harness", "tools"))
from distribution_anomalies import distribution_anomalies
from dangling_references import dangling_references
from incomplete_records import incomplete_records

def main():
    scores   = load_latest_scores()              # YOUR real output, not a synthetic fixture
    problems = []
    problems += ["scores: " + a for a in distribution_anomalies(scores)]
    problems += ["orphan company_id %s" % i for i in dangling_references(used_company_ids(), valid_company_ids())]
    problems += ["posting %d incomplete" % i for i in incomplete_records(postings(), ["parsed_skills", "score"])]
    if problems:
        print("data_quality: FAIL\n  " + "\n  ".join(problems)); sys.exit(1)
    print("data_quality: clean"); sys.exit(0)
```

## The vendoring boundary (important)

- **The harness ships the FRAMEWORK**: the pure primitives above + this convention. General, reusable.
- **The SPECIFIC checks live in YOUR project**: which fields are required, which ids must resolve, which output
  to sample — those depend on your schema, so they belong in *your* `qa/data_gates.py`, not the harness core.
- A check that turns out to be **general** (a new primitive useful to everyone) flows *back* into the harness
  `tools/` via a plan, like any other capability. Everything else stays yours. (Vendor-don't-fork.)

## For LLM pipelines: gate it deterministically

If the invariant you're checking only breaks *at scale* through the real model pipeline (slow +
nondeterministic), use the **cassette** layer (`tools/cassette_proxy.py`): record the model calls once, replay
them offline by request-hash so the end-to-end data-quality check runs in milliseconds, deterministically, on
every build. See `LATHE_COMMANDS.md` and the cassette docstring.
