# Lathe — Security Model

Lathe turns a *plan* (data describing functions + tests) into working code by having a model write
implementations that are then test-gated. **A plan is executed**, like a `Makefile`, `setup.py`, or an
`npm` postinstall script. The honest one-line summary: **only build plans you trust** — and for plans you
*don't* trust, build under `LATHE_SANDBOX=docker`.

This document describes the defense-in-depth that makes that boundary as small as possible, what each layer
guarantees, and where the irreducible limit is. It was hardened over ~18 rounds of the harness reviewing its
own code (`lathe review`), each round closing the bypasses an adversarial reviewer found.

---

## Threat model

Three distinct trust levels, three distinct exec surfaces:

| Surface | Who authors it | How it's contained |
|---|---|---|
| **The plan** (`OUT_DIR`, `FUNCTIONS`, `HEADER`, tests, …) | analyst model / a human | the **validator** — plans must be *pure data* |
| **The generated implementation** (`def f(): …`) | the local "implementer" model | the **sandbox** — tested in an isolated subprocess |
| **The integration/PRELUDE/artifacts** | the implementer model | containment + provenance + re-gating |

The validator is the strong boundary (it can fully constrain *data*). The generated implementation **cannot**
be statically constrained — it legitimately may use `os`, `subprocess`, etc. to implement real functions — so
its boundary is the **sandbox**, not static analysis.

---

## Layer 1 — the plan validator (`plan_validator.py`): plans are *pure data*

Built on **closed rules, not denylists** (a denylist of "dangerous things" is unbounded; an allowlist of
"safe things" is closed). A plan is rejected unless it is, structurally, only `NAME = literal` assignments:

1. **Data-only top level** — only assignments, imports, and a docstring. No `if`/`for`/`def`/calls at module level.
2. **Assignment targets are a single bare name** — no `FUNCTIONS[0]["tests"] = …` (subscript), no
   `obj.attr = …` (attribute), no `(a, ARTIFACTS) = …` (tuple-unpack). Each of those would mutate or rebind a
   value *after* the validator scanned it while the engine runs the real runtime value (scan-then-swap RCE).
3. **Imports are an allowlist** — only pure-compute stdlib (`re`, `json`, `math`, `collections`, …). `os`,
   `subprocess`, `io`, `http`, `gzip`, `ctypes`, `types`, `importlib`, … are all rejected. Imported *symbols*
   are checked too (`from operator import attrgetter as _x` is blocked, not just the module).
4. **Every exec'd value is a pure literal** — `HEADER`/`GLUE`/`INTEGRATION` and each `tests`/`functional`/
   `skeleton` field must be a literal constant, never `"imp"+"ort os"`, an f-string, `dict(…)`, or a name.
   So the string the validator scans is byte-for-byte the string the engine runs.
5. **All dunder access is blocked** (`__class__`, `__subclasses__`, `__globals__`, …) and the
   attribute-indirection around it (`getattr`/`setattr`/`attrgetter`/`methodcaller`) — this closes the
   Python sandbox-escape *class*, not individual instances.
6. **`MODULE_NAME` and function `name` must be identifiers**; **`OUT_DIR` is a literal string**; **every
   function needs ≥1 test** (an untested unit would auto-pass the gate).

## Layer 2 — the engine guards (`engine_v2.py`)

- **Validate the exact bytes that run** — the plan is read once; the same bytes are validated and exec'd (no
  TOCTOU re-read), and the validator is loaded only from trusted infra (never a plan-relative path).
- **Fail-closed gating** — if validation is requested but the validator can't run, the build is refused.
- **`OUT_DIR` containment** — output can't escape the working tree (checked on the engine itself, not only
  in `lathe.py`).
- **No infra/stdlib overwrite** — a plan can't name its module/artifact `engine_v2`, `json`, etc.; and the
  engine refuses to overwrite any file lacking a **line-1 provenance marker** (so it only ever overwrites
  files it generated — case-insensitive, marker can't be forged from file content).
- **Generated-code forgery guard** — a function body that frame-walks (`sys._getframe`, `f_back`/`f_locals`)
  or writes raw fds / `os._exit` is rejected before the sandbox runs it (it's trying to forge a test verdict).
- **RETIRE / PRELUDE** — only generated-output dirs or marker-bearing files can be archived (so a green plan
  can't delete `CLAUDE.md`/`docs/`); PRELUDE only `exec`s files whose **line 1** is the module marker.

## Layer 3 — the sandbox (`sandbox.py`)

The generated implementation + its tests run in an **isolated subprocess** (`LATHE_SANDBOX=subprocess`,
default for the autonomy loop): hard timeout + process-tree kill, secret-scrubbed env, throwaway cwd.

- **Unforgeable verdict (subprocess mode, best-effort)** — three known forge classes are closed: the parent
  hands the child a secret **nonce over stdin** (read before any untrusted code, then closed) so a printed or
  pre-written verdict is rejected; the child writes the verdict via a **frame-local** `os.write`/`json.dumps`
  captured before untrusted code runs, so a monkey-patched `os.write` can't intercept it; and Layer 2 rejects
  bodies that frame-walk for the nonce. **Caveat:** the body scan is a denylist (e.g. `getattr(frame,'f_back')`
  string-indirection can still reach a frame), so verdict integrity against a *deliberately adversarial
  implementer model* is **not** guaranteed in subprocess mode — **use `docker` mode** for that threat tier,
  where a forged "pass" still executed only inside a throwaway, network-less, read-only container.
- **`docker` mode** — throwaway container, no network, read-only rootfs, memory/pid caps: **true FS/network
  isolation**. This is the boundary for fully-untrusted plans/models, and the only thing that bounds
  memory-exhaustion DoS (`"x" * 10**10` needs no import, so no allowlist stops it).
- **`docker-ssh` mode** (added 2026-07-01) — the same container isolation, but the container runs on a REMOTE
  host over SSH (for machines where docker lives on the rig, not locally). Code + payload go in over stdin (no
  volume mounts); the nonce-framed verdict comes back. Fail-CLOSED on any ssh/docker error (never a silent
  downgrade to subprocess). **Verified end-to-end** on the rig: a container's network access to the model
  server returned `Network unreachable` (`--network none`), a rootfs write returned `Read-only file system`,
  no host files were visible, and a forged verdict line was correctly ignored. Enable with
  `LATHE_SANDBOX=docker-ssh` (or set `LATHE_DOCKER_SSH=<host>` with `docker` mode); `LATHE_DOCKER_IMAGE`
  overrides the base image. This is the recommended untrusted-plan boundary when local docker is unavailable —
  arguably stronger, since the code executes on a separate machine from the dev host.

## Layer 4 — the analyst call (`request_spec.py`)

SSRF/exfil guard: the analyst URL must be `http(s)` and resolve to a **loopback/private** address (IPv4-mapped
IPv6 and `0.0.0.0`/`::` are normalized/blocked, so the `169.254` metadata endpoint can't be reached). The
connection is **pinned to the vetted IP** so DNS-rebinding can't swap in an internal address at connect time.
`LATHE_TRUST_REMOTE_ANALYST=1` opts out (the autonomy loop strips it so a parent env can't).

---

## The irreducible floor

To *build* software, the engine must `exec` the implementation a model wrote, and that code can legitimately
be anything — so it cannot be statically allowlisted the way a *plan* can. Each unit is test-gated in the
sandbox first, output is confined to `OUT_DIR`, the harness's own files are overwrite-protected, and verdicts
are unforgeable — but **a plan you build is still code you run.**

- **Trusted plans** (you wrote them, or your analyst did): the in-process fast path is fine — like running
  your own `make`.
- **Untrusted plans / models**: build under **`LATHE_SANDBOX=docker`**. The subprocess sandbox contains
  crashes/hangs/escapes and forgery, but on stock Windows it is **not** filesystem-write confinement.

## Reproducing the audit

```
lathe review projects/agentic-harness/tools/plan_validator.py engine_v2.py \
  projects/agentic-harness/tools/sandbox.py projects/agentic-harness/tools/autonomy_live.py \
  projects/agentic-harness/tools/request_spec.py lathe.py self_feed_runner.py
```

This runs the harness's own multi-file, multi-lens (correctness + adversarial) reviewer over the security
core. Findings land in `projects/agentic-harness/docs/ce/review_{correctness,adversarial}.txt`.
