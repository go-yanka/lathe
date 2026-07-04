I've grounded the critique in the actual surface. Key finding up front: `cmd_verify` (lathe.py:381) does **not** assert anything — it reruns the engine and returns its exit code, printing "check the run report" as a hint. So the workflow's headline "self-host proof (byte-identical, 0 model calls)" is, against the real code, a vacuous pass. That plus `run_gates.py`'s skip-on-missing-file behavior and `is_relic`'s fail-open are the three structural holes everything else hangs off.

Here is the adversarial critique and the hardened spec.

---

# ADVERSARIAL CRITIQUE — `ship-release` / `lathe checkin`

## Class of failure being hunted
A step "passes" when (a) it is **skipped** (thinking-scaled off, missing input, no upstream), (b) it **produces nothing** but returns 0 (verify/gate hint-only), (c) it emits an **incomplete manifest** (a not-run step is *omitted* rather than recorded), or (d) it is satisfied **vacuously** (empty persona output, model asserts its own `notes_present:true`, a gate over an empty set). Below, each hole → the deterministic (code) guard that closes it. Every guard is an assertion the dispatcher runs on **structured facts**, never on model-printed prose.

---

## Phase 0 — Intake

**H0.1 — Crash before the stub exists = no record.** "Opens the manifest object immediately" is in-memory. A crash in Phase 0/1 leaves zero durable record, violating "always emitted."
→ **Guard:** first side effect of the run is to `write()` + `fsync()` a manifest stub to `docs/ce/<run_id>.release.manifest.json` with `verdict:"crashed"`, then register a `finally`/`atexit` that rewrites it with the terminal verdict. Process exit code is forced non-zero unless the on-disk file exists AND parses AND has a terminal verdict. Emission is a **post-condition the flow-runner asserts**, not a step that can be skipped.

**H0.2 — No upstream silently zeroes `behind`.** In `cmd_checkin`, `g(["rev-list","--count","HEAD..@{u}"])` returns non-zero when there's no upstream; `behind` stays `0`; the "behind-upstream" blocker never fires. On `--push` you then can't fast-forward-check against a phantom ref.
→ **Guard:** record `upstream_resolved:bool`. If `--push` and `upstream_resolved==false` → **refuse** (can't prove fast-forward). `behind` is only trusted when `upstream_resolved`.

**H0.3 — Thinking-level downgrade skips rigor.** casual (or simply *unset*) drops push, clean-rebuild, and drops to 1 persona. A lazy/hostile caller downgrades a canonical cut by omitting the flag.
→ **Guard:** `--cut` **forces** a minimum thinking floor of `medium` in code; `casual + --cut` is rejected. Record `thinking:{level, source: explicit|defaulted|floored}`.

---

## Phase 1 — Front-end

**H1.1 — `CLARIFIED_RELEASE.md` is checked for existence, not content.** A skill can write an empty file or `TODO`.
→ **Guard:** code parses required keys: `target_tag` matches `^v\d+\.\d+\.\d+$`, `bump_kind ∈ {patch,minor,major}`, `scope` non-empty. Missing/malformed → refuse.

**H1.2 — `notes_present:true` asserted by the model = vacuous.**
→ **Guard:** code *derives* it: `plans_changed = git diff --name-only <last_tag>..HEAD -- plans/`; for each, require a `CHANGELOG.md` entry referencing it. `notes_present` is computed, never trusted. On `--cut`, any plan changed since last tag without a note → refuse.

**H1.3 — Declared bump can lie (breaking change tagged `patch`).** "Refuse if bump direction undecided" is toothless — a model always picks *a* direction.
→ **Guard:** code computes a **minimum bump floor** from the diff: any change to CLI dispatch (`lathe.py` command table), `workflows.py`, or public signatures → `minor` floor; any changed **pin hash** for a previously-pinned function (behavior change) → at least `patch`. `target_tag`'s implied bump must be **≥ floor** and **> current `VERSION`**, else refuse. This also validates `bump_kind` against `target_tag` vs `VERSION` (a "major" whose tag is `v2.9.1` is a self-inconsistent lie → refuse).

**H1.4 — Assumption-audit passes with zero findings.** "Each HIGH must be resolved" is vacuously true when the auditor emits an empty list; and `LATHE_ASSUMPTION_POLICY=off` disables the gate entirely.
→ **Guard (three parts):**
  (a) The four release assumptions (**tag-collision, remote-is-canonical-not-fork, VERSION/CHANGELOG updated, every referenced pin committed**) are **code checks**, executed unconditionally — they don't depend on the model surfacing them.
  (b) `--cut` **forces** `LATHE_ASSUMPTION_POLICY≥high` (same FORCE pattern as `main()` already uses for `LATHE_VALIDATE_PLAN`); a stale/hostile env can't relax it. Record `env_forced`.
  (c) Each resolution is one of `{accept-as-intent, alternative, restate}` with a **non-empty body** and a decision hash written to `<run>.decisions.md`; a blanket "accept-all" with empty bodies is refused (matches existing "No blanket accept" doctrine).

---

## Phase 2 — Selection

**H2.1 — Empty/failed decider ⇒ adversarial-reviewer never selected ⇒ Phase 4 is skipped.** Phase 4 "persona generates" the cases; if the persona was never floored in, the whole adversarial gate evaporates.
→ **Guard:** code computes a **required-set from mode flags** — `{project-standards-reviewer, adversarial-reviewer}` always; `+security-reviewer` iff `--push`; `+provenance` iff `--cut`. Assert `required ⊆ selected`, else refuse. The **mandatory Phase-4 probes run as code regardless of selection** (see H4.5) — selection can only *add* personas, never gate away the spine.

**H2.2 — Empty `reason`/unknown persona strings.**
→ **Guard:** each selection entry requires non-empty `reason`, `source ∈ {CE,catalog}`, and a persona name that resolves to a real persona file (existence-checked). Unknown persona → refuse.

---

## Phase 3 — Work

**H3.1 — `run_gates.py` skips a check whose file is missing and reports "regression clean (0 checks)" → exit 0.** Delete/rename a gate script and it passes vacuously; worse, a manifest built from `run_gates` stdout simply *omits* the skipped gate, so the record looks clean.
→ **Guard:** the contract holds a **frozen EXPECTED gate list** (the 7 names). Before running, assert all 7 scripts **exist** (missing = refuse, overriding `run_gates`'s `continue`). After running, assert **every expected name produced PASS** and `count == 7`. A skipped/missing gate is a **FAIL, not an omission**. The manifest's `gates[]` is validated to contain exactly the 7 names.

**H3.2 — `gate_green = cmd_gate([])==0` can run zero gates** if the project path resolves wrong (wrong cwd/root).
→ **Guard:** subsumed by H3.1 — `gate_green` is only accepted if the 7-name assertion passed; a green from an empty run is rejected.

**H3.3 — Pristine defined *negatively* via `is_relic`, which fails open.** `is_relic` returns `False` on any exception and for anything outside a fixed extension list — so an untracked `.env`, a secret file, a stray binary, a `credentials.json` are **not relics** and don't block. `relics=[]` ⇒ "pristine."
→ **Guard:** define pristine **positively**: after `git add -A`, `git status --porcelain -uall` must be **empty** for a `--cut` (nothing untracked/ignored-but-forced remains). `is_relic` stays as a *diagnostic label*, never the gate.

**H3.4 — THE self-host proof is vacuous.** `cmd_verify` reruns the engine and returns its rc; a pin miss silently **regenerates fresh (a model call)**, the build passes, verify returns 0. "Byte-identical, 0 model calls" is asserted nowhere.
→ **Guard (three code assertions on structured engine output):**
  1. Run the engine with model calls **disabled** (`LATHE_OFFLINE=1` / a null endpoint that *raises* on any call) — a pin miss becomes a hard failure, not a silent regen.
  2. Parse the run report for `model_calls` and per-function pin resolution; assert `model_calls == 0` AND every function in scope resolved to a pin (`non_pinned == []`).
  3. `sha256` the rebuilt outputs vs the committed bytes; assert byte-identical.
  Verify returns pass **only** if all three hold.

**H3.5 — Verify over an empty set passes vacuously (docs-only or diff-scoped release).** "Across every *changed* plan" → a release that changed no plans verifies zero plans; self-host ratio = 1.0 over ∅.
→ **Guard:** for `--cut`, verify runs over the **full pinned surface** (every plan with pins), not the diff. Assert `plans_verified > 0` and `plans_verified == count(pinned plans)`; empty scope on `--cut` → refuse. `selfhost.ratio` is computed over the full surface, and the manifest records numerator/denominator so `1.0` over ∅ is impossible to fake.

**H3.6 — Ordering: verify runs on the working tree, then commit sweeps in *new* files that were never verified.**
→ **Guard:** **commit first**, then verify the *committed* tree (H4.3 does this in a clean worktree). The bytes you verify == the bytes you tag.

**H3.7 — Tag embeds a manifest digest, but the manifest isn't final until Phase 5 (cost/verdict).** Chicken-and-egg; the embedded digest can't cover the file that contains it.
→ **Guard:** the tag embeds `sha256` of the **frozen evidence sections** (`selection + work + selfhost + adversarial`), computed pre-push. Record `tag_digest`, `digest_algo`, and `digest_covers:[…section names…]`. Phase 5 re-computes and asserts the match, so the link is checkable, not decorative.

---

## Phase 4 — Adversarial gate

**H4.1 — Secret scan is under-scoped and misses common token types.** It scans `git show HEAD` (the single tip commit) but `git push` ships the whole range `@{u}..HEAD` — a secret in an earlier unpushed commit escapes. And `sk-[A-Za-z0-9]{20}` does **not** match `sk-ant-…` (breaks at the `-` after `ant`, only 3 alnum) → **Anthropic keys escape**; `gho_/ghs_/ghr_/github_pat_`, Slack `xox…`, Google `AIza…` are uncovered. It also fails **open** (any error in `git show` → empty stdout → "clean").
→ **Guard:** scan the **full push range** (`git diff <remote-tracking>..HEAD`, all new commits, staged pre-commit too — see HX.3), broaden the token set, add a high-entropy check, and fail **closed** (scanner error = refuse). Record `secret_scan:{range_scanned, commits_scanned, verdict}` so scope is auditable.

**H4.2 — Clean-checkout rebuild is thinking-scaled → skipped at casual/medium (the default).** The strongest proof for a *re-vendoring consumer* only runs at `high`; the default canonical cut ships without it.
→ **Guard:** for `--cut`, the clean-checkout rebuild is **mandatory at every thinking level**; thinking only scales it for non-cut checkpoints. `verdict:"released"` is unreachable unless `clean_checkout_rebuild == pass` when `cut`.

**H4.3 — Clean-rebuild passes because the scratch worktree shares the dirty tree's pin cache / model endpoint** (it "reproduces" by reading the same local pins, or silently regenerates).
→ **Guard:** the scratch worktree is a `git archive` of **HEAD only**; verify runs there with model calls **disabled** (H3.4); its outputs are compared byte-for-byte to HEAD's tracked outputs; assert `model_calls == 0` in the scratch run too.

**H4.4 — Tag-collision probe checks local tags only; remote fast-forward checked against stale `@{u}`.** A tag can exist on the remote but not locally; the tracking ref can be stale.
→ **Guard:** check `git tag -l` **and** `git ls-remote --tags <remote>`; collision on either → refuse. Fast-forward is checked against a **fresh** `git ls-remote <remote> <branch>`, not `@{u}`.

**H4.5 — Every Phase-4 case is persona-generated ⇒ empty persona output ⇒ vacuous pass.**
→ **Guard:** the **four probes (secret, clean-rebuild, tag-collision, provenance) are code**, run unconditionally by the dispatcher. The persona may *add* cases but cannot remove the mandatory four. `adversarial:{}` must contain all four keys with `pass|fail|skipped(+reason)` — a **missing key = incomplete manifest = refuse**.

**H4.6 — Provenance `notice_current:true` asserted by a model = vacuous.**
→ **Guard:** code diffs for **new third-party imports / new `LICENSE` files** since last tag and asserts each appears in `NOTICE.md`; asserts `NOTICE.md` and `CREDITS.md` exist, parse, and are non-empty. What can't be computed is recorded as `NOTICE`, never silently `true`.

---

## Phase 5 — Manifest

**H5.1 — "Always emitted" isn't guaranteed against a raising step.** → Closed by H0.1 (stub + `finally` + exit-code gated on file existence & parse).

**H5.2 — A not-run step is *omitted*, so an evaluator can't distinguish "not run" from "passed."**
→ **Guard:** fixed schema; **every top-level section required**; a not-run step is `{status:"skipped", reason}`, never absent. A **schema-validation gate runs before emit**; a manifest failing its own schema forces a verdict downgrade and non-zero exit. **The manifest validates itself.**

**H5.3 — `tokens:0 / usd:0` can mean "free" or "endpoint reported nothing."**
→ **Guard:** tokens summed from actual model-call records. `null` = unknown (endpoint gave no usage); `0` = ran and used none. Never conflate.

**H5.4 — `verdict` set by the skill ⇒ "released" without a push.**
→ **Guard:** `verdict` is **derived by code** from recorded facts. Invariant asserted before exit: `verdict=="released"` ⇒ `committed && pushed && remote_ack && (tag present) && all four adversarial probes pass && selfhost.model_calls==0 && gates==7/7`. `committed-local` ⇒ `committed && !pushed`. The skill cannot set `verdict`.

**H5.5 — Refused with an empty `refusal[]` is uninformative.**
→ **Guard:** `verdict=="refused"` ⇒ `len(refusal) ≥ 1`, else schema violation.

---

## Cross-cutting

**HX.1 — Bare `lathe checkin` today runs `cmd_checkin` directly** — no manifest, no verify, weak regex, fail-open behind. The contract must **wrap** it.
→ **Guard:** `checkin` dispatches to the ship-release **contract runner**; the legacy `cmd_checkin` body becomes an internal step invoked *by* the contract. No `--no-contract` escape exists. This is the "route THROUGH, not around" requirement made literal.

**HX.2 — Rigor-disabling env (`LATHE_STRICT` unset, `LATHE_ASSUMPTION_POLICY=off`, `LATHE_TRUST_PLAN=1`).**
→ **Guard:** for `--cut`, the contract **FORCEs** `LATHE_STRICT=1` and `LATHE_ASSUMPTION_POLICY≥high` (the same non-`setdefault` FORCE `main()` already applies to `LATHE_VALIDATE_PLAN`/`LATHE_VALIDATOR_PY`). Record `intake.env_forced` + any override attempt.

**HX.3 — Secret scan runs *after* commit** (`cmd_checkin` commits, then scans HEAD) — the secret is already in local history before detection; if the scan errors, push proceeds.
→ **Guard:** scan the **staged diff pre-commit** and refuse before committing; scan again post-commit over the push range (H4.1). Fail-closed both times.

**HX.4 — Signed tag "if a key is configured" silently downgrades to unsigned.**
→ **Guard:** `tag_signed` derived from `git verify-tag`. If signing was requested but the tag is unsigned → refuse. At `high`, signing is required for `--cut`.

**HX.5 — Concrete contradiction: the manifest's human render trips the pristine gate.** `is_relic` lowercases the path and matches `basename_lower == 'run_report.md'`; the proposed mirror `RUN_REPORT.md` lowercases to `run_report.md` → flagged as a **relic** → blocks the very checkin that emits it.
→ **Guard:** write the manifest render as `docs/ce/<run_id>.release.report.md` (not `RUN_REPORT.md`), or exempt the manifest path from `is_relic`. Do **not** name any emitted artifact `run_report.md` in any case.

---

# HARDENED WORKFLOW (implementer's spec)

Legend: **AUTO**=dispatcher code (non-bypassable) · **GATE**=code assertion, refuse on fail · **YOU**=analyst/skill output, gated by the following code check.

### Phase 0 — Intake (AUTO)
- Mint `run_id`; **write + fsync manifest stub** (`verdict:"crashed"`); register `finally` rewrite. [H0.1]
- Resolve `VERSION`, `HEAD`, branch, `@{u}` → set `upstream_resolved`. [H0.2]
- Parse mode `{cut, push}`, thinking; **floor thinking≥medium if `--cut`**; record `thinking.source`. [H0.3]
- **FORCE** `LATHE_STRICT=1`, `LATHE_ASSUMPTION_POLICY≥high` on `--cut`; record `env_forced`. [HX.2]
- **Refuse** if `--push && !upstream_resolved`. [H0.2]

### Phase 1 — Front-end
- **1a CLARIFY (YOU→GATE):** parse `CLARIFIED_RELEASE.md`; validate `target_tag` regex, `bump_kind`, `scope`. [H1.1] Compute `bump_floor` from diff; assert declared bump ≥ floor and > `VERSION`. [H1.3] Compute `notes_present` from `<last_tag>..HEAD` plan diff vs CHANGELOG; refuse on `--cut` if any changed plan lacks a note. [H1.2]
- **1b ASSUMPTION-AUDIT (AUTO+YOU→GATE):** run the **four code assumptions** unconditionally; require each resolved with a non-empty typed decision in `<run>.decisions.md`; no blanket accept. [H1.4]

### Phase 2 — Selection (AUTO)
- Compute `required_set` from mode; assert `required ⊆ selected`. [H2.1]
- Validate each entry (`reason` non-empty, `source` valid, persona file exists). [H2.2]

### Phase 3 — Work
1. **GATE — 7/7 standing gates.** Assert all 7 scripts exist (missing=refuse); assert `count==7` and every name PASS. [H3.1/H3.2]
2. **GATE — pristine (positive).** `git add -A` then assert `git status --porcelain -uall` empty on `--cut`; compute `behind` only if `upstream_resolved`. [H3.3]
3. **AUTO — commit** (before verify). [H3.6]
4. **GATE — self-host proof.** Engine with model calls **disabled** over the **full pinned surface**; assert `model_calls==0`, `non_pinned==[]`, `plans_verified==count(pinned)>0`, and rebuilt bytes `sha256`-identical to committed. [H3.4/H3.5]
5. **AUTO (on `--cut`) — cut + tag.** Bump `VERSION`, stamp `CHANGELOG.md`, `git tag -a v<VERSION>` embedding `tag_digest = sha256(frozen evidence sections)`; sign if configured, else record `tag_signed:false`. [H3.7/HX.4]

### Phase 4 — Adversarial gate (GATE; four probes are CODE)
- **Secret scan** over full push range + staged pre-commit; broad token set + entropy; fail-closed. [H4.1/HX.3]
- **Clean-checkout rebuild** from `git archive HEAD` in a scratch worktree, model calls disabled, byte-compared; **mandatory on `--cut`** at all thinking levels. [H4.2/H4.3]
- **Tag-collision + fresh non-ff probe** against `git ls-remote`. [H4.4]
- **Provenance** (on `--cut`): new third-party imports/LICENSEs ⊆ `NOTICE.md`; NOTICE/CREDITS non-empty. [H4.6]
- All four keys required in the manifest; any fail → refuse (nothing pushed). [H4.5]

### Phase 3b — Publish (AUTO)
- **Push** only if all above green: `remote = pick(LATHE_REMOTE, config.checkin.remote, "")`; `git push [remote HEAD] --follow-tags`. No upstream → stays local, recorded (not an error).

### Phase 5 — Manifest (AUTO, `finally`)
- **Derive `verdict`** from facts (H5.4 invariant); enforce `refused ⇒ refusal≥1` (H5.5); run schema-validation gate; emit JSON + `.release.report.md` render (**never** `run_report.md`, HX.5). Exit code gated on the file existing + parsing + having a terminal verdict. [H5.1/H5.2]

---

# HARDENED MANIFEST SCHEMA
`docs/ce/<run_id>.release.manifest.json` — every section **required**; a not-run step is `{status:"skipped",reason}`, never omitted; the manifest is validated against this schema before emit.

```
run_id, invocation:"ship-release", cli:"lathe checkin", timestamp, duration_ms
intake:      { branch, head_before, version_before, upstream, upstream_resolved:bool,
               mode:{cut:bool, push:bool},
               thinking:{level, source:"explicit|defaulted|floored"},
               env_forced:[{var, value, was_overridden:bool}] }          # HX.2, H0.2/3
front_end:   { clarify:{target_tag, bump_kind, scope,
                        bump_floor, bump_ok:bool, notes_present:bool},   # H1.1-1.3 (all code-derived)
               assumptions:[{id, text, materiality, resolution_kind, resolution_body, decision_hash}],
               mandatory_assumptions_all_resolved:bool, decisions_file } # H1.4
selection:   [{persona, source:"CE|catalog", grade, reason}]
             required_set:[…], required_subset_ok:bool                    # H2.1/2.2
work:        { gates:{ expected:7, ran:7, results:[{name, verdict, last_line}], all_pass:bool },  # H3.1
               pristine:{ porcelain_empty:bool, behind:int|null, blockers:[] },                    # H3.3/H0.2
               commit:{ committed:bool, commit_sha },                                              # H3.6
               verify:{ scope:"full_pinned_surface", plans_verified:int, pins_expected:int,
                        pins_hit:int, non_pinned:[], model_calls:int, byte_identical:bool,
                        offline_enforced:bool } }                                                  # H3.4/3.5
selfhost:    { ratio:float, numerator:int, denominator:int }             # over full surface; ∅ impossible  H3.5
adversarial: { secret_scan:{verdict:"pass|fail", range_scanned, commits_scanned},                 # H4.1/HX.3
               clean_checkout_rebuild:{verdict:"pass|fail|skipped", reason, model_calls:int},      # H4.2/4.3
               tag_collision:{local:bool, remote:bool, verdict},                                   # H4.4
               fast_forward_ok:bool,
               provenance:{status:"pass|fail|skipped", notice_current:bool, credits_current:bool,
                           unattributed:[]} }                                                      # H4.6
publish:     { committed:bool, commit_sha, tag, tag_signed:bool, tag_verified:bool,
               tag_digest, digest_algo:"sha256", digest_covers:[…],                                # H3.7/HX.4
               pushed:bool, remote, refspec, remote_ack:bool }                                     # H5.4
cost:        { models:[{name, tokens_in:int|null, tokens_out:int|null, usd:float|null, reason}],
               tokens_in_total, tokens_out_total, usd_total }            # null≠0                  H5.3
verdict:     "released" | "committed-local" | "refused" | "crashed"       # code-derived only      H5.4
refusal:     [ blockers… ]                                                # len≥1 iff refused      H5.5
schema_ok:   bool                                                        # self-validation result H5.2
```

---

# NON-BYPASSABLE INVARIANTS (assert before exit)
1. On-disk manifest exists, parses, `schema_ok==true`, terminal `verdict` set — else exit non-zero. [H0.1/H5.1/H5.2]
2. `verdict=="released"` ⇒ `gates.all_pass && verify.model_calls==0 && verify.non_pinned==[] && all four adversarial probes pass && (cut ⇒ tag && clean_checkout_rebuild.pass) && pushed && remote_ack`. [H4.2/H5.4]
3. `verdict=="refused"` ⇒ `len(refusal)≥1` and `pushed==false && tag==null`. [H5.5]
4. `gates.expected==gates.ran==7`; a missing gate script is a FAIL, not an omission. [H3.1]
5. On `--cut`: `env_forced` shows STRICT=1 and assumption-policy≥high; `thinking.level≥medium`. [HX.2/H0.3]
6. Nothing under `docs/ce/` emitted by the run is named `run_report.md` (case-insensitively). [HX.5]

---

### The three additions that matter most (beyond the sketch)
1. **Make `cmd_verify` assert, not hint** — offline engine + `model_calls==0` + byte-`sha256` compare over the full pinned surface. As written it is the single biggest vacuous pass in the design.
2. **Freeze the expected gate list in the contract** so `run_gates.py`'s skip-on-missing can't silently drop a check or leave it out of the manifest.
3. **Every "the persona surfaces X" becomes "code runs X, persona may add to it"** — assumptions (four), adversarial probes (four), provenance, and `notes_present`/`bump_floor` are all code-derived; the skill supplies bodies and extra cases but can never gate the spine away.

Relevant files for the implementer: `/home/user/lathe/lathe.py` (`cmd_checkin` L1614, `cmd_verify` L381, `main` FORCE pattern L1688), `/home/user/lathe/projects/agentic-harness/tools/checkin_logic.py` (`is_relic` fail-open, `checkin_blockers`), `/home/user/lathe/projects/agentic-harness/qa/run_gates.py` (skip-on-missing L26), `/home/user/lathe/projects/agentic-harness/tools/workflows.py` (add `ship-release` + `CONTRACTS`), `/home/user/lathe/docs/OPERATING_CONTRACT_DESIGN.md` (§16 seed, manifest post-condition L34/50).