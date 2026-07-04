# Lathe — Pins & Determinism Reference

*How a spec + tests + model become a content hash — the "pin" — and why that makes every rebuild
byte-identical with zero model calls. This is the mechanism behind "same spec, same code, every time."
Everything here is traceable to `engine_v2.py` and `projects/agentic-harness/tools/pin_deps.py`.*

## The one-paragraph model

An LLM is non-deterministic: ask it for the same function twice and you may get different code. Lathe does
**not** try to make the model deterministic. Instead, the *first* time a function's code passes its gate,
Lathe stores that exact accepted code under a hash of its **contract** — the function name, its spec prompt,
its tests, and the implementer model id. On every later build, Lathe recomputes the hash; if it matches a
stored pin (and the pin still passes), it **replays the stored bytes and never calls the model**. Determinism
is a property of *reuse*, not of generation. The model's randomness is sidestepped, not tamed.

---

## 1. The unit that gets pinned

A **plan** declares `FUNCTIONS`, each a dict:

```python
FUNCTIONS = [
  {"name": "slugify", "prompt": "<the spec: what it must do>", "tests": ["assert slugify('A B')=='a-b'", ...]},
]
```

- **`name`** — the function's identity.
- **`prompt`** — the spec the implementer model is given (the human's intent, written by the analyst).
- **`tests`** — the acceptance oracle; the code is accepted only if these pass in the sandbox.

The code itself is **not** in the plan. Code is a *build output*, produced by the implementer model from the
prompt and gated by the tests.

## 2. The pin key — hashing the contract

For each function the engine computes (`engine_v2.py:630`):

```python
pkey = sha256( name + "\x00" + prompt + "\x00" + repr(tests) + "\x00" + fmodel ).hexdigest()
```

Four inputs, `\x00`-delimited so they can't run together ambiguously:

| Input | Why it's in the key |
|---|---|
| `name` | different function → different pin |
| `prompt` | the spec changed → the intent changed → re-derive the code |
| `repr(tests)` | the acceptance contract changed → the old code may no longer be correct |
| `fmodel` | a different implementer model is a different build input (provenance) |

**What is *not* in the key:** the generated code. The code is the **value** the key maps to. The hash is of
the *contract*; the pin is the accepted *answer* to that contract. This is the crucial inversion — the pin
says "for this exact spec+tests+model, here is the code that passed," and any byte of contract drift produces
a different key and forces a fresh derivation.

## 3. Where pins live

```python
PIN_FILE = os.path.join(OUT_DIR, ".pins.json")     # engine_v2.py:510
```

`.pins.json` sits next to the built module. It's a plain JSON object: `{ pkey: "<accepted code string>" }`.
It is:

- **checked in** — your reproducibility cache travels with the repo;
- **written atomically** — a temp file + `os.replace` so a crash never leaves a half-written pin
  (`.pins.json.tmp` is the engine's own transient, explicitly exempted by the stale gate);
- **plain text** — you can read exactly which contract produced which code.

## 4. First build vs rebuild — the two lanes

### First build (cache miss)
1. Compute `pkey`. It's not in `.pins.json`.
2. The implementer model generates up to `LATHE_TRIES` candidates (best-of-`K` if the function sets
   `"select": 2/3`). Each candidate is run against the tests **in the sandbox** (`validate`).
3. A passing candidate (the judged-cleanest if `K>1`) becomes the **winner**. Under STRICT it must also clear
   the rigor gates (mutation-score, etc.) before it may pin.
4. `pins[pkey] = winner` (`engine_v2.py:721`) — the accepted code is stored under its contract hash.
5. Failing candidates + the exact failing test are banked in `tools/_fn_fails/` (failure-as-asset), and the
   analyst sharpens the spec — **no escalation to a bigger model**.

### Rebuild (cache hit)
1. Compute `pkey`. It *is* in `.pins.json`.
2. **Re-validate before trusting it** (`engine_v2.py:650`):
   ```python
   if not _dep_stale and pkey in pins and validate(pins[pkey], name, tests, solved_ns):
       winner, source = pins[pkey], "pinned"
   ```
   The pinned code is re-run against the current tests in the sandbox. A pin is **never** replayed blindly —
   if it no longer passes (or a dependency changed, §5) it's discarded and the function is rebuilt.
3. On a clean hit: the stored bytes are reused, **zero model calls**, in milliseconds. Byte-identical output.

**This is the determinism claim, precisely stated:** *identical* `name`+`prompt`+`tests`+`model` → identical
`pkey` → the same stored code is replayed. Change any one of the four → cache miss → the model regenerates,
and the new code must re-pass the gate (it may differ byte-for-byte; the *contract* is what's guaranteed, not
the model's output on a fresh roll).

## 5. Transitive invalidation — the "make without depfiles" hole, closed

A subtle correctness trap: function `B`'s pinned code calls function `A`. If `A` was **regenerated this run**,
`B`'s pin was verified against the *old* `A` — replaying it would be stale-but-green (its own tests still
pass, but against a changed dependency). Lathe catches this (`engine_v2.py:647`, logic in
`tools/pin_deps.py`):

- `code_refs(code, names)` derives `B`'s dependencies by scanning the pinned code for references to other
  function names — no separate depfile, the code *is* the dependency record.
- `pin_stale_by_deps(pinned_code, fresh_names)` returns `True` if any function regenerated this run appears
  in `B`'s code. Freshly-regenerated names are tracked in `_fresh_fn_names` in plan order.
- A stale-by-deps pin is invalidated and `B` is rebuilt against the new `A`:
  `pin INVALIDATED — references a dependency regenerated this run; rebuilding`.

## 6. Cold rebuild — the honest demo

Two different "rebuilds" prove two different things:

- **Rebuild from pins** (keep `.pins.json`): every function is a cache hit → byte-identical, zero model
  calls, seconds. *"The code was never the source."*
- **Cold rebuild** (evict `.pins.json`): every function regenerates on the model and **re-passes its gate
  live**. The bytes may differ from last time; the *contract* holds. *"Different bytes, same contract — and
  the gate decides, not the model's confidence."*

Both are legitimate. The first demonstrates reproducibility; the second demonstrates that acceptance is
gated, not memorized.

## 7. What is *not* pinned (the honest caveat)

- **Glue / header code** is hand-written and **unpinned** — it carries no contract hash (it's marked as such
  in the provenance count, and gated separately by gate-the-glue when substantive). So a naive
  `rm -rf src && rebuild && diff` will **not** be byte-empty: the glue isn't regenerated. Never run that
  version as a determinism demo.
- **Artifacts** (ARTIFACTS-mode files) are pinned by a *structural* signature, not functional replay — the
  functional check happened at generation (`engine_v2.py:818`).
- **The engine/CLI trunk itself** (`engine_v2.py`, `lathe.py`, `sandbox.py`, …) is ordinary
  hand-/LLM-authored Python, not leaf-function plans, so it is not pin-reproducible *by Lathe*. Lathe
  industrializes the well-specified leaf-function core; the trunk is built the normal way.

## 8. Pins as provenance

Because the pin ties **accepted code ↔ (name, spec, tests, model)**, `.pins.json` plus the run ledger is a
provenance record by construction: for any gated function you can say which model produced it, against which
tests, under which spec — and prove the current bytes still pass. That's the artifact the compliance pitch
rests on (`MARKETING_SALES_KIT.md §6`), and it exists as a side effect of building this way, not as
after-the-fact paperwork.

---

## Quick reference

| Concept | Where | Detail |
|---|---|---|
| Pin key | `engine_v2.py:630` | `sha256(name‖prompt‖repr(tests)‖model)` |
| Pin store | `OUT_DIR/.pins.json` | `{pkey: code}`, atomic write, checked in |
| Reuse (re-validated) | `engine_v2.py:650` | replays stored bytes only if it still passes |
| Pin write | `engine_v2.py:721` | stores the judged-best gated candidate |
| Transitive invalidation | `pin_deps.py`, `engine_v2.py:647` | rebuild if a referenced dep was regenerated |
| Retry budget | `LATHE_TRIES` (default 3) | Rule of Three, then escalate to you |
| Best-of-N | plan `"select": N` | collect N passers, judge the cleanest |
| Not pinned | glue/header, trunk | hand-written, unpinned by design |

*Verify it yourself: build a plan, inspect `.pins.json`, delete the generated function body and rebuild
(byte-identical from the pin), then evict the pin and cold-rebuild (regenerates, re-passes, may differ).*
