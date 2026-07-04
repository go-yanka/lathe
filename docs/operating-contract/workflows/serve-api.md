Grounded in the actual code (`lathe_api.py`, `api_logic.py`, `mcp_safe.py`), here is the adversarial critique. I read the real `serve()`, `Handler`, `_build_job`, `_run_json`, and the guard functions — several holes below are not hypothetical, they are what the shipped code does today versus what the proposed workflow claims.

---

# PART A — HOLES (where a step is skipped / produces nothing / emits an incomplete manifest / passes vacuously)

## A group — the "always-emitted manifest" is not actually guaranteed

**H1 — L1/L2 refusal emits NOTHING (the headline claim is false in the shipped code).**
`serve()` does `sys.exit("...REFUSING...")` on missing token and on bad bind *before any file is written*. The proposal says L0 "opens the lifecycle manifest in `refusing` state" — but "open" is in-memory; `sys.exit` never flushes it. A refusal today produces zero bytes on disk. The audited-refusal artifact does not exist.
**Deterministic close:** L0 must `open(path, "x")` (O_CREAT|O_EXCL) and `write()+os.fsync()` a complete, schema-valid `refusing` manifest to `docs/ce/serve-<runid>.manifest.json` *before* L1 runs, then `assert os.path.exists(path)` and re-read+parse it (a boot self-test) before proceeding. L1/L2/L3/L5 refusal is a *rewrite* of `verdict:"refused"`, never a fresh create. If the self-test read fails, refuse.

**H2 — crash between boot and shutdown freezes the manifest at `serving` forever (incomplete).**
Finalization (`shutdown_at`, `uptime_s`, all `rollup` counters) is written "at shutdown." SIGKILL / OOM / `os._exit` / power loss skips it. The counters live only in memory, so they die with the process. The manifest is permanently INCOMPLETE and no code notices.
**Deterministic close:** (a) `rollup` is **never** an in-memory counter — it is *derived by scanning `requests.ndjson`* at finalize. (b) Write the pid into the manifest at L6. (c) A reaper (`lathe serve --finalize <runid>`, also run at the top of every new `serve`) scans `docs/ce/serve-*` for manifests stuck in `serving` whose pid is dead, recomputes `rollup` from the ledger, and stamps `lifecycle.verdict:"crashed", shutdown_at:<detected>`. Signal handlers (SIGTERM/INT/HUP) + `atexit` do the graceful finalize; the reaper covers SIGKILL. Finalization is idempotent (flag+lock, first writer wins).

**H3 — runid collision overwrites a prior run's manifest.**
If runid is timestamp-second or reused, a second `serve` clobbers the first record.
**Deterministic close:** runid = uuid4 (or pid+monotonic+os.urandom). L0's `open(path,"x")` fails closed on collision → mint again / refuse.

**H4 — no schema validation ⇒ "emitted" can mean `{}` or half a manifest.**
"Always emit" is vacuous if the emitted object is missing `frontend`, `preflight`, `rollup`, etc. A skipped L3 with no `frontend` key is indistinguishable from a crash.
**Deterministic close:** a `MANIFEST_SCHEMA` (required keys + types) validated **on every write**. Missing/typewrong required key → the write is rejected and replaced with `verdict:"schema-fail"` carrying the offending key list. Every ndjson line gets the same treatment (see H10). The validator is code in the M phase, non-bypassable.

## B group — the L-gates pass vacuously

**H5 — L1 token gate is presence-only; `LATHE_API_TOKEN=dev` passes.**
The proposal even names this ("is it a real secret or `"dev"`?") but leaves it to L3's *judgment*. At exposed tier that is a code-level hole: a one-char token satisfies the gate.
**Deterministic close (code floor, not judgment):** at `exposure_tier=exposed`, refuse unless `len(token) >= 32` **and** `token not in WEAK_TOKENS={"dev","test","changeme","secret","token","password","admin"}` **and** shannon-entropy ≥ threshold. Record `token_entropy_ok:bool`. Loopback tier may waive (recorded as `token_check:"waived-loopback"`).

**H6 — L2 sandbox gate is VACUOUS: `LATHE_SANDBOX=docker` is a string that proves no isolation.**
`_run_json` runs the child as a plain `subprocess.run([PY, "lathe.py"...])` — there is **no docker anywhere in the code**. A caller sets `LATHE_SANDBOX=docker`, binds `0.0.0.0`, passes L2, and remote plan code executes *in-process on the host*. The proposal only asserts real isolation inside L5's `high` tier — meaning at default/medium a non-local bind ships with fake isolation.
**Deterministic close (unconditional at exposed tier, not thinking-gated):** L2 runs a *liveness* probe — spawn a child through the real execution path and assert it is genuinely containerized: child prints `/proc/1/cgroup` + hostname + a probe for host-FS unreachability; parent asserts the markers differ from the host and the host root is not visible. If isolation is not *proven*, refuse `reason:"sandbox-unproven"`. String equality on the env var is never accepted as evidence.

**H7 — bind/tier classified by string match; `localhost`, `::`, `::1`, hostnames evade or misclassify.**
Tier = `loopback if bind∈{127.0.0.1,localhost}`. `localhost` can resolve off-loopback via `/etc/hosts`; `::` (IPv6 all-interfaces) is non-local but isn't matched as exposed by name; a DNS hostname is unhandled.
**Deterministic close:** resolve the bind to IP(s) and classify with `ipaddress.ip_address(x).is_loopback` over *every* resolved address. Any non-loopback address ⇒ `exposed`. Unresolvable/ambiguous bind ⇒ refuse (fail-closed). Tier is computed from resolved IPs, never from the literal string.

**H8 — thinking level is attacker-influenceable ⇒ skip L3+L5.**
"casual ⇒ skip L3, L5 auth-only." If `LATHE_THINK` is read from an environment the caller can influence (or an exposed operator sets it low), the two adversarial phases vanish on an exposed surface.
**Deterministic close:** effective_think = `max(LATHE_THINK, floor(exposure_tier))` clamped in code — `exposed ⇒ floor=high`. `LATHE_THINK` is **not** in `_ENV_ALLOW` (per-request cannot set it). Manifest records `think_requested` and `think_effective`; `effective < floor` is unrepresentable.

**H9 — L3 passes vacuously on an empty/malformed analyst ledger.**
L3's gate is `blocking_unresolved==0`. If the model returns `[]` (found nothing), or errors, or returns non-JSON, there are zero HIGH items ⇒ zero unresolved ⇒ PASS. The judgment step certifies safety by doing nothing.
**Deterministic close:** the HIGH checklist is **code-seeded**, not model-enumerated. Code injects a fixed mandatory set at exposed tier — `{token_entropy, env_allow_can_weaken_gate, run_timeout_finite, concurrency_cap, rate_limit, bind_scope}`. The model may add items and may *propose* resolutions; code then asserts **every seeded item** has `resolution ∈ {accept,override,mitigated}` with non-empty `justification`. Malformed/absent analyst output ⇒ `blocking_unresolved = len(seeded_high)` ⇒ refuse. Empty ledger can no longer pass.

## C group — L4 / L5 vacuity and an ordering contradiction

**H10 — L4 selection can seat zero personas and still "succeed."**
If the data file is edited empty or scaling floors to 0, selection produces nothing.
**Deterministic close:** code asserts `security-reviewer ∈ personas` unconditionally and `len(personas) >= 1`; schema requires `selection.personas` non-empty with non-empty `why` per entry (drawn from a code enum of reasons). Can't seat security-reviewer ⇒ refuse.

**H11 — ORDERING BUG: L5 "probes the live bound socket" but the socket isn't bound until L6.**
As written, L5 cannot hit a real surface, so every "probe" degrades to a *unit test of a function* (`assert auth_ok('',tok)==False`) — a placeholder that passes without exercising the wire. That is textbook vacuous.
**Deterministic close:** reorder boot. **L6a** binds the socket on the configured address but behind an *accept barrier* (handler refuses all traffic except from the in-proc preflight client, gated by a one-time nonce). **L5** then issues *real HTTP requests* through that socket. Only if all probes pass does **L6b** drop the barrier, flip `serving`, and print the listen line. Bind failure (`OSError`, addr-in-use) ⇒ L-M `refused, reason:"bind-failed:<errno>"`.

**H12 — L5 probes pass with no evidence attached.**
A probe that records `verdict:"pass"` with no `sent/expected/got` is unfalsifiable.
**Deterministic close:** each probe row must carry `{name, target(url+method), sent, expected, got, verdict}`. Code treats `got is None` or missing `expected` as **FAIL**. `all_passed = every row verdict=="pass" AND has evidence`. Concretely, the mandatory probe set (each a real HTTP round-trip through L6a):
- `auth-missing`→401, `auth-blank`→401, `auth-wrong`→401, `auth-right`→200.
- `path-escape`: POST plan `../../etc/passwd` → 400 (`is_within_root` false).
- `flag-injection`: goal `--help` / `-x` → 400 (`reject_flags`).
- `env-catalog-leak`: GET `/v1/env` → assert response contains only `{name,group,role,default}` keys and **no value matching any live env value** (regex the resolved env values against the body; any hit ⇒ FAIL).
- `body-oversize`: `Content-Length` past cap → 413.

**H13 — env-strip probe (`_SECRET_HINT`) is vacuous if it tests the filter, not a real child.**
**Deterministic close:** set two canaries (`LATHE_API_TOKEN=<c1>`, `LATHE_SECRET_CANARY=<c2>`), spawn a *real* child through `_run_json`'s path that dumps `os.environ`, assert **neither** canary present, and record the child's captured-env **digest** as evidence. A pass with no child env digest is rejected.

**H14 — "constant-time auth" is unprovable at the wire ⇒ any runtime probe is a placeholder.**
**Deterministic close:** replace the timing claim with a deterministic **pin assertion** — assert the sha256 pin of `api_logic.py` matches the reviewed-good pin in `.pins.json` (the auth path is pinned generated code using `hmac.compare_digest`). Record `probe:auth-const-time, method:"pin-hash", pin:<sha>`.

**H15 — api-contract probe passes vacuously when the contract doc is absent.**
**Deterministic close:** exposed tier + missing/unparseable `docs/API_PROPOSAL_REST.md` ⇒ refuse (`reason:"contract-spec-missing"`). Can't certify conformance to an absent spec.

## D group — the per-request ledger loses lines (the "one gated line per request" guarantee is false today)

**H16 — R0/R1 rejections write NOTHING to the ledger.**
In the real `Handler`, `_authed()` sends 401 and returns; `_body()`→None sends 400; `classify_build_body` fail sends 400 — **none writes a ledger line**. Every rejected request is unrecorded. There is also no ledger at all in the current code.
**Deterministic close:** wrap the entire request in `handle_one_request` (or a decorator over `do_GET/do_POST`) with a `finally:` that appends **exactly one** ledger line for every request — including auth failures, malformed JSON, 404s, and handler *exceptions* (`reason:"handler-exception"`). The append is the last act of request handling and cannot be skipped by an early `return`/`raise`.

**H17 — async gap: a request whose job is still running at SIGKILL leaves no line.**
R-M writes "one line per request," but the line needs R3's gate verdict, which isn't known until the async job finishes. Crash mid-job ⇒ the request happened but is invisible.
**Deterministic close:** **two-phase ledger.** Phase-1 (`intake` line) is appended+fsynced at end of R1, *before* enqueue: `{reqid, verdict:accepted|rejected, guards, intake}` with `gate:"pending"`. Phase-2 (`resolution` line, same reqid) written by the worker at job completion. The reaper reconciles any `pending` older than the run timeout to `outcome:"lost"`. "One request → at least one durable line" holds across crash; rollup dedups by reqid taking the latest.

**H18 — 6 engine-invoking endpoints have no contract, no delegation, no ledger.**
The design only routes `plan`/`goal` through R2. But `/v1/gate`, `/v1/verify`, `/v1/trace`, `/v1/review` all call `_run_json` — real subprocess work — with no nested manifest and (post-fix) no ledger. `/v1/env`, `/v1/plans`, `/v1/metrics`, `/v1/builds/<id>` also do work.
**Deterministic close:** the R1 firewall + ledger wrapper covers **all** endpoints (see H16). No code path may call `_run_json` without passing through the wrapper (enforce by making `_run_json` assert a per-request context token minted by R1; raw calls raise). Side-effecting endpoints either delegate through their target invocation's contract (record `nested_manifest_ref`) or are classed `read-only` in code with that class recorded in the line. An unclassified endpoint calling `_run_json` refuses.

**H19 — concurrent threads corrupt the ndjson.**
ThreadingHTTPServer + many appenders → interleaved partial lines → "one parseable line per request" broken.
**Deterministic close:** a single serialized writer: `with _LEDGER_LOCK: os.write(fd, line.encode()+b"\n"); os.fsync(fd)` writing one complete line per call (or a queue drained by one writer thread). Never `print`/buffered-append from worker threads directly.

## E group — the delegation (R2/R3) reports success vacuously

**H20 — `build_ok` derived from `rc==0`, not from the gate.**
`_build_job` goal path: `result = {"build_ok": rc==0, ...}` when no METRICS block is found. A `do` subprocess that exits 0 for *any* reason (including doing nothing) reports `build_ok:True`. The gate verdict is fabricated from an exit code.
**Deterministic close:** `build_ok` must come from the child's structured manifest `gate.verdict` only. Missing METRICS/manifest ⇒ `build_ok:False, outcome:"error", reason:"no-gate-verdict"` (fail-closed). `rc==0` is never promoted to a gate pass.

**H21 — nested_manifest_ref can dangle; no handshake exists.**
The child isn't told a runid and isn't required to emit a manifest at a predictable path; the parent only regexes stdout. A crashed child ⇒ `nested_manifest_ref` points at a nonexistent file while the line still says `passed`.
**Deterministic close:** parent **mints the child runid** and passes `LATHE_RUNID=<child>` in the (stripped, allow-listed) env; child contractually emits `docs/ce/<child>.manifest.json`. R3 asserts the file exists and parses before writing `outcome:"passed"`; absent ⇒ `outcome:"error", reason:"nested-manifest-missing"` regardless of scraped `build_ok`.

**H22 — caller can DISABLE rigor gates through the allow-list, so "the delegated run runs its own STRICT gates" is false.**
`_ENV_ALLOW` includes `LATHE_STRICT`, `LATHE_REGRESSION_PROOF`, `LATHE_GATE_GLUE`, `LATHE_TEST_ACK`, `LATHE_MUTATION_SCORE`, `LATHE_TEST_KIND`. `env:{"LATHE_STRICT":"0"}` turns strict OFF on the delegated build. This is the central contradiction of the whole design.
**Deterministic close:** the rigor vars become **raise-only**. Code compares each requested override to the server's floor and drops any that would *loosen* (STRICT 1→0 dropped; 0→1 allowed). At exposed tier the rigor vars are removed from the allow-list entirely. Every drop is recorded in `env_overrides_dropped` with `reason:"would-weaken-gate"`.

## F group — resource / DoS holes that let the hot path produce garbage or die

**H23 — unbounded body read (`_body` trusts `Content-Length`).** → cap; over-cap ⇒ 413 + ledger line.
**H24 — default request timeout is `None` (unbounded builds).** `LATHE_RUN_TIMEOUT` unset ⇒ infinite. → hard code default (e.g. 900s); exposed tier requires explicit finite value or refuses at L2.
**H25 — unbounded concurrency (every POST spawns a daemon thread + subprocess; `_JOBS_MAX` bounds only history).** → semaphore cap; over-cap ⇒ 503 + `rejected, reason:"concurrency-cap"`. Exposed tier without a cap refuses at L2.
**H26 — eviction can pop an in-flight job.** `_JOBS.pop(next(iter(_JOBS)))` evicts oldest by insertion, which may be `queued`/`running`; the worker then writes to a dead key and `/v1/builds/<id>` 404s a live job. → eviction skips non-terminal status; if all in-flight, refuse new job with 503 (never evict a live one). Ledger resolution line is written before the `_JOBS` cache update, so eviction never loses the record.
**H27 — raw child stdout leaks into results/ledger.** goal path stores `{"output": out[-2000:]}` — raw child text (may contain goal/paths/secrets), returned via `/v1/builds/<id>`. → ledger line carries only digests + manifest ref; a schema-validator rejects any line with free-text raw output; error fields are coded enums.

## G group — the spine can be bypassed entirely

**H28 — `python lathe_api.py` calls `serve()` directly, around the flow-runner.**
The `__main__` block runs `serve()` with none of L0–L5. The design's own principle ("bare commands route THROUGH their contract, not around it") is violated by the shipped entrypoint.
**Deterministic close:** `serve()` asserts a contract-context token that only the flow-runner sets; called raw it refuses (`reason:"spine-bypass"`). The module entrypoint invokes the dispatcher/flow-runner, which runs L0–L6 then calls `serve`. No path reaches `serve_forever` without the L-spine having produced a manifest.

---

# PART B — HARDENED WORKFLOW

## Scope L — lifecycle (run once, via the flow-runner; `serve()` refuses if invoked outside it — H28)

| # | Type | Phase | Hardened action + the deterministic guard it cannot skip |
|---|------|-------|-----------------------------------------------------------|
| **L0** | AUTO | Intake | Assert contract-context token (else refuse `spine-bypass`, H28). Mint uuid4 `runid` (H3). Resolve bind→IPs, set `exposure_tier` via `is_loopback` over all resolved addrs; unresolvable⇒refuse (H7). Freeze config struct. Compute `think_effective = max(LATHE_THINK, floor(tier))` (H8). **`open(manifest,"x")`, write schema-valid `verdict:"refusing"`, fsync, re-read self-test** (H1, H4). Run the crashed-run reaper over prior `serve-*` (H2). |
| **L1** | GATE | Front-end | Token gate. Empty⇒refuse `no-token`. Exposed tier: `len>=32 ∧ ∉WEAK ∧ entropy≥thresh`, else refuse `weak-token` (H5). Record `token_entropy_ok`. Refuse ⇒ rewrite `verdict:"refused"` → L-M. |
| **L2** | GATE | Front-end | Bind/sandbox gate on **resolved** tier (H7). Non-local ⇒ **sandbox-liveness probe**: spawn child, prove containerization from markers; unproven⇒refuse `sandbox-unproven` (H6). Exposed tier additionally requires finite `LATHE_RUN_TIMEOUT` (H24) and a `concurrency_cap` (H25); missing⇒refuse. |
| **L3** | YOU (analyst, gated) | Front-end (assume) | Exposure assumption audit over the **code-seeded** HIGH checklist (H9). Every seeded item needs an explicit resolution+justification; malformed/empty analyst output ⇒ `blocking_unresolved=len(seeded)` ⇒ refuse. Skippable only at `loopback+casual`, and only then — the skip is recorded as `assumption_audit_ran:false, skip_reason:...` (H4). |
| **L4** | AUTO | Selection | Seat the fixed control-plane triad; assert `security-reviewer ∈ set ∧ len≥1` (H10). `selection.mode:"fixed-control-plane"`; each persona carries non-empty enum `why`. |
| **L6a** | AUTO | Work (bind, barriered) | Bind socket **behind an accept-barrier** (only the nonce-bearing preflight client is served). Bind failure⇒refuse `bind-failed:<errno>` (H11). |
| **L5** | YOU (analyst, gated) | Adversarial (pre-flight) | Run the mandatory probe set as **real HTTP round-trips through L6a** (H11): auth 4-way, path-escape→400, flag-injection→400, env-catalog-leak scan, body-oversize→413 (H12), env-strip canary with child-env digest (H13), auth-const-time pin assertion (H14), and exposed-tier contract check (missing spec⇒refuse, H15). Any probe without evidence = FAIL. Any FAIL ⇒ refuse `preflight-<probe>` → L-M. |
| **L6b** | AUTO | Work (open) | Drop the accept-barrier, register the two-phase ledger writer (single serialized appender, H19), flip `serving`, print listen line. |
| **L-M** | CODE (M) | Manifest | Schema-validated write (H4). Boot writes `serving`; graceful shutdown finalizes with **ledger-derived rollup** (H2); reaper finalizes crashes as `crashed`. Idempotent finalize. Emitted on every L1/L2/L3/L5 refusal. |

## Scope R — per-request (all code; wraps EVERY endpoint; ledger in `finally`)

| # | Type | Phase | Hardened action + guard |
|---|------|-------|-------------------------|
| **R-wrap** | CODE | — | `handle_one_request` wrapped: mint `reqid`; **guaranteed `finally:` appends exactly one ledger line** for every request incl. auth-fail/400/404/exception (H16). `_run_json` asserts the per-request context token — no engine call escapes the wrapper (H18). Body read capped (H23). |
| **R0** | GATE | Intake | `auth_ok` constant-time; fail⇒401, phase-1 line `rejected/auth`. |
| **R1** | GATE | Intake firewall | `classify_build_body`→{plan|goal}; `is_within_root` on all paths; `reject_flags` on all free strings; env overrides through `env_allowlist`, then **raise-only filter** drops any rigor-var that would weaken a gate (exposed tier: rigor vars not allow-listed at all) (H22); env values length/control-char bounded. Fail⇒400, phase-1 `rejected/<guard>`. **Phase-1 `accepted` line fsynced before enqueue** (H17). |
| **R2** | AUTO | Work (delegate) | Concurrency semaphore (over-cap⇒503 `concurrency-cap`, H25). Mint **child runid**, pass `LATHE_RUNID` + stripped/allow-listed env (H21). Enqueue; worker re-enters `build --json`/`do` as subprocess with hard timeout (H24). Eviction skips non-terminal jobs (H26). |
| **R3** | GATE | Adversarial | `build_ok` read from child's **manifest `gate.verdict`**, never `rc==0` (H20). Missing/dangling nested manifest ⇒ `outcome:"error"` (H21). `done+build_ok:false` = built-but-refused, surfaced verbatim. |
| **R-M** | CODE (M) | Manifest | Worker writes **phase-2 resolution line** (same reqid) via the serialized writer *before* touching `_JOBS` cache (H26). Only digests + `nested_manifest_ref`; schema-validator rejects raw output (H27). Reaper stamps stale `pending`→`lost` (H17). |

---

# PART C — EXACT HARDENED MANIFEST FIELDS

### Lifecycle — `docs/ce/serve-<runid>.manifest.json` (created O_EXCL at L0, fsynced, schema-validated on every write)

```
runid(uuid4), invocation:"serve", schema_version, pid                    # H3, H2
intake:    { bind, resolved_ips:[...], exposure_tier, tier_source:"resolved-ip",
             sandbox_mode, sandbox_proven:bool,                          # H6
             token_present:bool, token_entropy_ok:bool, token_source:"env",   # H5
             env_allow:[...], rigor_vars_raise_only:bool,               # H22
             run_timeout_finite:bool, concurrency_cap:int|null,          # H24,H25
             jobs_max, body_cap_bytes, started_at, host_fingerprint,
             think_requested, think_effective, think_floor }             # H8
frontend:  { assumption_audit_ran:bool, skip_reason?,                    # H9 (present even when skipped, H4)
             seeded_high:[...], ledger:[{item,materiality,resolution,justification}],
             blocking_unresolved:int }
selection: { mode:"fixed-control-plane", personas:[{name,why,source}],   # H10 (non-empty, security-reviewer required)
             scaled_by:"exposure_tier" }
preflight: { boot_order:["L6a-bind","L5-probe","L6b-open"],              # H11
             probes:[{name,target,method,sent,expected,got,verdict,evidence_ref}],  # H12
             all_passed:bool }
lifecycle: { verdict:"serving"|"refused"|"crashed"|"schema-fail",        # H1,H2,H4
             refuse_reason?, boot_at, shutdown_at, uptime_s, signal?,
             finalized_by:"shutdown"|"reaper" }
rollup:    { ...ALL fields derived by scanning requests.ndjson, never in-memory:  # H2
             requests_total, accepted, rejected_auth, rejected_input,
             rejected_concurrency, builds_ok, builds_refused, jobs_failed,
             jobs_lost, jobs_evicted, tokens_total, cost_total_usd }
models:    [ ...ids scraped from nested manifests ]
manifest_emitted_at, manifest_finalized_at
```

### Per-request — `docs/ce/serve-<runid>/requests.ndjson` (two lines per request; single serialized fsync'd writer)

```
# phase-1 (intake), fsynced before enqueue — H16,H17
{ reqid, runid, phase:"intake", ts, remote_addr, endpoint, method, endpoint_class:"delegating"|"read-only",  # H18
  intake:{ kind:"plan"|"goal"|"n/a", value_digest(sha256), auth:"ok"|"reject" },
  guards:{ path_within_root:bool, reject_flags:"pass"|"blocked",
           env_overrides_requested:[...], env_overrides_applied:[...],
           env_overrides_dropped:[{name,reason}], body_bytes },          # H22,H23
  verdict:"accepted"|"rejected", reason? }

# phase-2 (resolution), written by worker before _JOBS update — H20,H21,H26,H27
{ reqid, runid, phase:"resolution", ts,
  delegate:{ invocation:"do"|"build", child_runid, child_argv_digest,
             nested_manifest_ref, nested_manifest_present:bool },        # H21
  gate:{ job_status:"done"|"failed", build_ok_source:"nested-manifest",  # H20
         build_ok:bool, outcome:"passed"|"built-but-refused"|"error", error_code? },
  metrics:{ queue_ms, run_ms, tokens, cost_usd, model } }               # digests/enums only, no raw output — H27
```

**Non-negotiables, all in code, none in the skill:** L0's O_EXCL fsync'd `refusing` manifest (H1); ledger-derived rollup + crashed-run reaper (H2); schema validation on every manifest and ledger write (H4); exposed-tier token-entropy floor (H5); sandbox-liveness proof (H6); resolved-IP tier (H7); think-floor clamp (H8); code-seeded HIGH checklist (H9); bind-before-preflight with real HTTP probes carrying evidence (H11,H12); the `finally` request wrapper covering every endpoint (H16,H18); two-phase fsync'd ledger (H17); raise-only rigor env (H22); `build_ok` from nested `gate.verdict` never `rc==0` (H20); child-runid handshake with existence assertion (H21); and `serve()` refusing outside the flow-runner (H28).

The single highest-value fix is **H22 + H6**: without raise-only rigor env and a real sandbox proof, an exposed `serve` runs remote-submitted code in-process with the caller free to switch STRICT off — which makes every downstream gate the manifest reports on a fiction.