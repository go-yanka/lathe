# Try Lathe yourself — the shakedown experiment

Reproduce the v2.62.6 live shakedown: build a real, non-trivial module (a shunting-yard arithmetic
evaluator) through the harness and watch the Reporter. Full findings write-up:
`docs/SHAKEDOWN_v2.62.6_TERMINAL_DRIVE.md`.

**The folder:** `examples/shakedown/` — `calc.py` is the plan; builds land in `examples/shakedown/build/`.

---

## Level 0 — no model needed (30 seconds)

Prove determinism + inspect the harness without any model running. From the repo root:

```bash
python3 lathe.py verify examples/hello.py     # → "REPRODUCIBLE … byte-stable, 0 model calls"
python3 lathe.py status                       # board + endpoint health
python3 lathe.py whatis sandbox               # which file is the live one for a capability
python3 lathe.py dups                          # duplicate-logic report
```

---

## Level 1 — build the evaluator for real (needs a model)

### 1. Prerequisites
- Python 3.11+
- The `claude` CLI installed and logged in  → `claude --version` should print. (Or point the endpoints at
  any OpenAI-compatible server / a local model — see step 2 alt.)

### 2. Stand up the two endpoints (analyst + implementer)
Lathe wants an **analyst** (writes the spec/repairs) on `:8787` and an **implementer** (writes code) on
`:8089`. The bundled `claude_proxy.py` shims either one over the `claude` CLI.

```bash
# IMPORTANT: on Linux/macOS you must set CLAUDE_BIN — the proxy defaults to a Windows path (issue #46)
export CLAUDE_BIN="$(command -v claude)"

# analyst (a strong model) on 8787
CLAUDE_PROXY_MODEL=sonnet python3 claude_proxy.py --port 8787 &

# implementer (a cheap model — this is the point) on 8089
CLAUDE_PROXY_MODEL=haiku  python3 claude_proxy.py --port 8089 &

# confirm both are actually live
curl -s 127.0.0.1:8787/health ; echo
curl -s 127.0.0.1:8089/health ; echo
python3 lathe.py status          # should say "READY to build"
```

*Alt (your own local model):* skip the 8089 proxy and
`export LOCAL_OPENAI_URL=http://127.0.0.1:<your_port>/v1/chat/completions`. Set
`HARNESS_CLAUDE_URL` similarly for the analyst.

### 3. Build the plan
```bash
export HARNESS_CLAUDE_URL=http://127.0.0.1:8787/v1/chat/completions
export LOCAL_OPENAI_URL=http://127.0.0.1:8089/v1/chat/completions

LATHE_MUTATION_SCORE=0.5 \
  python3 lathe.py build examples/shakedown/calc.py
```
- `LATHE_MUTATION_SCORE=0.5` arms the mutation gate (tests must kill mutants).
- (Historical note: this plan used to need `LATHE_TRUST_PLAN=1` for the GLUE+INTEGRATION import catch-22 —
  **issue #44, now fixed**: the engine auto-prepends `from calc import *` to the generated integration test,
  so GLUE+INTEGRATION builds through the validated path with no trust-bypass.)

Expect: `tokenize` passes fast; `to_rpn`/`eval_rpn` may take **2–3 tries each** on the cheap model (the retry
loop) — that's the system working. Finish: `DONE … gated-green`.

### 4. Verify it actually works
```bash
cd examples/shakedown/build && python3 -c "
import calc
print(calc.evaluate('2 + 3 * 4'))      # 14.0
print(calc.evaluate('2 ** 3 ** 2'))    # 512.0  (right-associative)
try: calc.evaluate('1 / 0')
except calc.CalcError: print('1/0 correctly rejected')
"; cd -
```

### 5. See the "delete the code, rebuild free" trick (determinism)
```bash
rm examples/shakedown/build/calc.py
LATHE_MUTATION_SCORE=0.5 python3 lathe.py build examples/shakedown/calc.py
# → all functions REUSED from pins, tok_total: 0 (byte-identical, no model calls)
```

---

## Watch the Reporter (the source of truth) in real time

While a build runs, in another terminal:

```bash
# live, stage-by-stage during the run:
tail -f projects/runs/$(ls -t projects/runs | head -1)

# the sealed, tamper-evident record after each command (outcome, gates, per-role tokens, sha256):
python3 -c "import json,glob,os; d=json.load(open(sorted(glob.glob('docs/ce/*.manifest.json'),key=os.path.getmtime)[-1])); import pprint; pprint.pprint({k:d[k] for k in ('run_id','outcome','gates','usage','integrity')})"
```

---

## Issues this shakedown surfaced — all now FIXED in main (PRs #52–#60)
- **#46** — proxy on Linux/macOS resolved `CLAUDE_BIN` via a Windows path; now resolves via `shutil.which`
  and `/health` probes the binary. Fixed.
- **#44** — GLUE + INTEGRATION import catch-22; the engine now auto-prepends `from <module> import *`. Fixed.
- **#45** — `do "…" --assume` could collapse a goal to trivial helpers; under-delivery now HOLDs
  deterministically under `LATHE_STRICT=1`. Fixed.
- **#47** — the TEST-KIND gate now banks a synthetic record so the analyst-repair loop engages instead of
  dead-ending. Fixed.

Cleanup: `pkill -f claude_proxy` (kills the two proxies).
