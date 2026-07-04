I've read the real implementations (`cmd_clean` L570, `cmd_checkpoint` L442, `cmd_dups` L511, `checkpoint.py`, `pristine_gate.py`, `stale_gate.py`, `resource_dups_gate.py`, `dup_report.py`, `workflows.py`, item 17). The proposed workflow describes guards that the current code does not implement, and several proposed gates would pass vacuously. Here is the adversarial critique and hardened spec.

---

# maintain-tree — Adversarial critique + hardened spec

## Ground truth that breaks the proposal's assumptions

- **No manifest emitter, no pin-replay, no orphan-pin computation exists in code.** `cmd_clean`, `cmd_checkpoint`, `cmd_dups` all `return 0` without writing any record. Every "M" step and the `no_regress`/`checkpoint_restorable`/`lossy_clean_proof` gates are *specified but unbuilt* — so today they are NOTHING, and a naive implementation makes them vacuous.
- **`cmd_clean` (L570) is destructive with zero coupling to a snapshot.** It moves files immediately. The proposal's central guard ("no quarantine without a recorded snapshot-or-skip") does not exist; nothing enforces it.
- **`snapshot()` (checkpoint.py:37) returns `''` on *any* failure**, silently — indistinguishable at the call site from "not a repo."
- **`restore()` is `git checkout <sha> -- .`** — restores content of tracked paths but does **not** delete files created after the snapshot, and cannot recover gitignored files. "Rollback is real" is only partly true.
- **`cmd_clean` re-scans and quarantines ALL unparseable files itself** — it takes no confirmed subset, so the proposed "uncertain → KEEP" judgment step (3) is silently overridden by the execute step (4).

---

## Holes → deterministic check that closes each

**H1 — Snapshot-failure masquerades as success.** `snapshot()` returns `''` on git-lock/index-write/empty-tree failure. If `is_repo` is true but sha is empty, the flow may proceed believing it is protected.
→ *Check:* after snapshot assert `re.fullmatch(r'[0-9a-f]{40}', sha)` AND `git cat-file -t <sha> == "commit"` AND `git rev-parse CKPT_REF == sha`. `is_repo && invalid-sha` ⇒ **ABORT clean** (fail-closed). The `skipped` state is legal *only* when `not is_repo(INNER)`.

**H2 — `checkpoint_restorable` gate is a no-op ("dry-restore").** There is no dry-restore in `restore()`; a stub that does nothing passes.
→ *Check:* gate must (a) `git rev-parse --verify CKPT_REF^{commit}` == recorded sha; (b) `git cat-file -t sha`==commit; (c) `git cat-file -e sha:<path>` for **every** path clean is about to move — the snapshot must provably contain each. No mutation, but real object-existence assertions, not a claimed dry-run.

**H3 — `no_regress` pin-replay passes vacuously over the empty set.** "0 model calls, byte-identical" is trivially true when 0 pins are replayed.
→ *Check:* enumerate `tools/.pins.json` **before** clean → `pins_before`. Replay must assert `pins_replayed == pins_before` AND `model_calls == 0` (hard counter, not observed) AND every replayed artifact `sha256 == pin.sha`. `pins_before == 0` is recorded and, in high mode, **flagged** (a zero-pin tree is suspicious, not green).

**H4 — `lossy_clean_proof` compares `.pins.json` to itself.** clean never touches `.pins.json`, so `pins_before == pins_after` always — the proof is satisfied even after quarantining a module a pin depends on.
→ *Check:* do not diff the JSON. For each pin resolve its **owning plan + generated module path**; `lost_pins[] = {pin : owner now under _archive/ or failing ast.parse}`. Nonempty ⇒ **auto-rollback + REFUSE**.

**H5 — Execute step overrides the judgment step.** `cmd_clean` quarantines everything unparseable; the analyst's "keep uncertain" set is ignored.
→ *Check:* clean must take an explicit allow-list from step 3: `lathe clean --only <confirmed.json>`. Guard: `quarantined ⊆ confirmed`; a file not on the list that clean would move ⇒ **abort**. Without a list, clean is dry-only.

**H6 — The snapshot-before-move guard is not in the code path.** Described in prose; `cmd_clean` has no such coupling.
→ *Check:* flow-runner passes a token; `cmd_clean` refuses to move unless invoked with valid `--snapshot <sha>` or `--snapshot-skip <reason>` (reason accepted only when `not is_repo`). Bare `lathe clean` ⇒ `--dry` forced.

**H7 — Bare commands route AROUND the contract.** `cmd_clean/checkpoint/dups` execute directly; the destructive move is reachable without spine, snapshot, or manifest.
→ *Check:* the three entrypoints delegate to the maintain-tree flow-runner. The move logic is guarded by a module-level token the flow-runner sets; absent ⇒ dry-only. This is the non-bypassable-spine requirement made real.

**H8 — Manifest not emitted / emitted late on the REFUSE+rollback path.** No emitter exists; a throw during rollback would skip it.
→ *Check:* emission is in a dispatcher-level `finally` wrapping the whole invocation. Process exit is gated on `os.path.isfile(manifest_path)`; if absent, write a minimal `{verdict:REFUSE, refuse_reason:"manifest_incomplete"}` before non-zero exit.

**H9 — Manifest emitted INCOMPLETE but PASS** (empty `gates[]`/`personas[]`/`moves[]`).
→ *Check:* a deterministic schema validator runs before any PASS is allowed. For PASS it requires: an entry for **each** of the 5 gate names with `verdict==PASS`; `personas[]` nonempty, every entry with nonempty `why`; every persona has a matching `contributors[]` row (no vacuous selection); `work.scan` present with numeric counts; `lossy_clean_proof.pin_replay_model_calls==0`; `ts_end>ts_start` and `elapsed_s≈ts_end-ts_start`. Any failure forces `verdict=REFUSE`.

**H10 — "not computed" indistinguishable from "computed: none found."** `orphan_pins:[]`, `lost_pins:[]`, `unparseable:[]` can all be emitted without running the analysis.
→ *Check:* every analysis field is `null` until its producing step runs, then the concrete list (possibly `[]`). Validator: in medium a required-but-`null` field ⇒ REFUSE; `[]` (computed-empty) ⇒ OK. This is the single most important anti-vacuity rule.

**H11 — Gate crash counted as pass.** Flow that checks `==1` for fail treats an import-error/traceback (other nonzero) ambiguously; a "skipped" gate reads as green.
→ *Check:* run each gate in-process capturing `(returncode, exception)`; `PASS iff returncode==0 and no exception`. Any exception ⇒ `verdict=ERROR`, treated as REFUSE. No gate may be **absent** from `gates[]`.

**H12 — Post-clean tree never re-verified pristine.** `cmd_clean` moves files but never asserts the result parses; a transient IO read error can quarantine a good file, or a broken import graph survives.
→ *Check:* after clean, call `pristine_gate.offenders()` and `stale_gate.candidates()` in-process; both must be empty. Nonempty ⇒ REFUSE (do not claim pristine). Also re-run `ast.parse` on each *retained* file, distinguishing a genuine `SyntaxError` from `OSError` (never quarantine on IO error — retry, then keep).

**H13 — `fail_bank_capped:{to:40}` claimed but move can silently fail.** L619 `except Exception: pass`. Dir may still hold >40.
→ *Check:* after capping, re-count `_fn_fails`; `to` = actual post-count; assert `≤40`; any raised move recorded in `fail_bank_errors[]`; nonempty errors ⇒ do not report success for that sub-step.

**H14 — clean can eat the engine's live atomic-write temp.** `cmd_clean._STALE` matches `\.tmp$`, so `.pins.json.tmp` (the engine's in-flight pin write) is quarantined — but `stale_gate` explicitly *skips* it (stale_gate.py:38). Inconsistent regexes + no concurrency guard ⇒ clean can corrupt a concurrent build.
→ *Check:* clean must reuse stale_gate's exact predicate (skip `*.pins.json.tmp`). Before any move, assert no build lock present (engine writes/holds a lock); lock present ⇒ abort with `refuse_reason:"concurrent_build"`.

**H15 — Snapshot silently omits gitignored files.** `git add -A` won't stage ignored paths; if a to-be-quarantined plan/module is gitignored, snapshot cannot recover it (only `_archive/` can).
→ *Check:* for each path clean will move, verify `git cat-file -e <sha>:<path>`; misses go to `snapshot_missing_paths[]`. Clean still proceeds (it never deletes; `_archive/` is the second recovery channel) but the manifest records the reduced-protection honestly, and the lossy proof treats those paths as archive-only-recoverable.

**H16 — Auto-rollback assumed complete but `checkout -- .` doesn't delete post-snapshot files.** After rollback, `_archive/` and any clean-created dirs persist; rollback is unverified.
→ *Check:* auto-rollback takes its own safety snapshot first (reuse `cmd_checkpoint restore` semantics), then after restore re-computes the pre-clean inventory (file count + pin set + `pristine_gate` empty) and asserts it matches the recorded pre-state. `rolled_back:true` only if that verification passes; else escalate to `verdict:REFUSE, refuse_reason:"rollback_unverified"` (never claim a rollback that wasn't confirmed).

**H17 — Destructive flag unchallenged if the skill front-end is skipped.** The "block only when a flag contradicts a default" logic lives in the (skippable) skill.
→ *Check:* code-level argv parse in the flow-runner: any of `--delete/--purge/--force-delete` ⇒ HARD refuse unless `<run>.decisions.md` carries an explicit confirm token minted this run. Not delegated to the model.

**H18 — dups advisory misread as complete.** `dup_report` scans `tools/` only, `min_nodes≥12`, skips `_`/`test_` files and `_`-prefixed functions — cannot see plan-level or private-helper dups.
→ *Check:* not blocking (advisory by design), but `work.dups.scope{dirs_scanned, min_nodes, excluded_globs}` is a required field so coverage is explicit; absence ⇒ REFUSE (H10).

**H19 — Selection can yield zero personas and proceed.**
→ *Check:* `data-integrity-guardian` is mandatory for maintain-tree (min 1). Selection yielding 0 ⇒ refuse. Every persona in `personas[]` must have a `contributors[]` row with nonempty `found_or_did` (H9).

**H20 — Manifest skipped on the `--dry`/casual path** because "nothing happened."
→ *Check:* emission is unconditional (H8). Dry manifest carries `mode:"dry"`, `verdict:PASS`, `work.quarantine.moves:[]`, and the full `candidates[]` (would-move set) — a dry run that records no candidates is still a real record.

**H21 — src→dest mapping lost on collision-rename.** L585 renames dest to `name.1.py`; nothing records the actual destination, so recoverability is unverifiable.
→ *Check:* clean returns `moves[]=[(src, actual_dest, why)]`; flow asserts `len(moves)==moved` and `os.path.exists(dest)` for each; `work.quarantine.moves[]` nonempty iff `moved>0`.

---

## Hardened workflow (typed steps + non-bypassable guards)

**Phase 0 — Intake (AUTO/code).** classify→maintain-tree; assign `run_id`; set thinking; **pre-state inventory** = `{file_count, parseable_pct, fail_bank_size, pins[]}` recorded *before anything*. `is_repo(INNER)` resolves snapshot-live vs skip. Parse argv for destructive flags (H17). Acquire maintain-tree lock; abort if a build lock exists (H14). Bare `clean/dups/checkpoint` route to the full sweep via the flow-runner (H7).

**Phase 1 — Front-end (skill+model, gated).** `assume` scope audit, each HIGH assumption fail-closed to safe default in `<run>.decisions.md`. Code-level flag guard (H17) runs regardless of whether the skill fired.

**Phase 2 — Selection.** mandatory `data-integrity-guardian` + thinking-scaled `maintainability/reliability/adversarial` reviewers, each `why` tied to the artifact it will judge; ≥1 enforced (H19).

**Phase 3 — Work (ordered, each guarded):**
1. **A scan** — enumerate `plans/`+`tools/`, `ast.parse` each distinguishing `SyntaxError` from `OSError` (H12); run `dup_report` recording `scope` (H18); compute `orphan_pins`/`orphan_modules` deterministically (else field=`null`, H10). Pure report.
2. **A pre-clean snapshot** — `snapshot(INNER,"pre-clean")`; validate sha (H1); verify every to-be-moved path exists in the snapshot tree, misses→`snapshot_missing_paths[]` (H15). If `not is_repo`: record `skipped_reason`. **Guard: clean cannot run without a valid `--snapshot <sha>` or `--snapshot-skip <reason>` token (H6).**
3. **Y (gated) triage** — analyst classifies each candidate corrupt vs WIP → writes `confirmed.json`. Autonomous rule: uncertain→KEEP.
4. **A clean --only confirmed.json** — moves confirmed set to `_archive/<date>-cleanup/`, caps `_fn_fails`. Guard `quarantined ⊆ confirmed` (H5). Returns `moves[]` (H21). Re-count fail-bank → actual `to` + `fail_bank_errors[]` (H13). Reuse stale_gate predicate (skip `.pins.json.tmp`, H14). **Post-move re-verify `pristine_gate.offenders()`+`stale_gate.candidates()` both empty (H12).**
5. **Y (gated) dup decision** (high only) — cross-module → `consolidate-upstream` (fold into owning plan + queue rebuild task, never hand-edit) or `accept` (rationale). Medium: report-only.

**Phase 4 — Adversarial gate (code; each in-process, crash=REFUSE, none absent, H11):**
- **G pristine** — `pristine_gate.offenders()` empty.
- **G stale_gate** — `stale_gate.candidates()` empty.
- **G resource_dups_gate** — no duplicate resource (blocking).
- **G no_regress** — pin-replay: `pins_replayed==pins_before ∧ model_calls==0 ∧ every sha256 matches` (H3).
- **G checkpoint_restorable** — object-existence assertions on ref+sha+every moved path (H2).
- **Adversarial probe — lossy proof:** resolve each pin's owner; `lost_pins = owners now archived/unparseable` (H4); nonempty ⇒ **auto-rollback (safety-snapshot-first) → re-verify inventory match (H16) → verdict REFUSE**.

**Phase 5 — Manifest (code, `finally`, never optional, H8/H20):**
- **A post-clean snapshot** `pristine` (validated, H1).
- **M** emit `docs/ce/<run>.manifest.json`, **run schema validator (H9/H10)**; validator failure forces REFUSE; exit gated on `isfile(manifest_path)`.

---

## Hardened manifest schema (`docs/ce/<run>.manifest.json`)

Rule enforced by the validator: **any required analysis field is `null` until computed; `[]` means computed-empty. `null` in a required slot ⇒ REFUSE (H10).**

- **base:** `run_id, ts_start, ts_end, elapsed_s (==ts_end−ts_start±ε), invocation:"maintain-tree", cli, mode:"dry"|"live", thinking_level, models[]|"none", tokens{in,out,total}, cost_usd, verdict:"PASS"|"REFUSE"|"ERROR", refuse_reason`.
- **front_end:** `assumptions[]{id,text,materiality,resolution,fail_closed_default}, decisions_path|null, destructive_flags[], confirm_token|null`.
- **selection:** `personas[]{name,lens,bucket,score,why}` (≥1, `data-integrity-guardian` required).
- **work.scan:** `{files_scanned, parseable, unparseable[]|null, io_errors[], stale_targets[]|null, fail_bank_size, orphan_pins[]|null, orphan_modules[]|null, dup_scope{dirs_scanned,min_nodes,excluded_globs}}`.
- **work.pre_snapshot:** `{ref, sha|null, sha_valid:bool, taken:bool, skipped_reason|null, snapshot_missing_paths[]}`.
- **work.quarantine:** `{candidates[], confirmed[], kept_uncertain[], moves[]{src,actual_dest,why}, archive_dir, fail_bank_capped{from,to_actual}, fail_bank_errors[], subset_ok:bool}`.
- **work.dups:** `{scope{...}, cross_module[]{shape_nodes,members[]}, same_module[], decisions[]{shape,action,rationale,rebuild_task_id?}}`.
- **work.contributors[]:** `{name, found_or_did}` — one per selected persona.
- **adversarial.gates[]:** exactly 5, `{name, returncode, exception|null, verdict:PASS|FAIL|ERROR, detail}`.
- **adversarial.lossy_clean_proof:** `{pins_before, pins_after, pin_replay_model_calls (==0), pins_replayed, lost_pins[]|null, rolled_back:bool, rollback_verified:bool}`.
- **final:** `post_snapshot{ref,sha,sha_valid}, final_artifact{pristine:bool, checkpoint_ref, archive_dir, manifest_path}, schema_valid:bool`.

## Guaranteed artifact / non-bypassable guards
Provably-pristine tree + durable rollback anchor (`refs/harness/ckpt` validated sha) + `<run>.manifest.json`. Code enforces: no move without a valid snapshot-or-skip token; quarantine ⊆ analyst-confirmed set; never delete; never auto-rewrite generated code; post-move pristine re-verified; lossy clean auto-rolls-back with verified inventory match; every gate present and crash=REFUSE; manifest emitted and schema-validated in a `finally`, even on REFUSE; bare `clean/checkpoint/dups` execute only through the flow-runner.

Relevant paths: `/home/user/lathe/lathe.py` (cmd_clean L570, cmd_checkpoint L442, cmd_dups L511), `/home/user/lathe/projects/agentic-harness/tools/checkpoint.py`, `/home/user/lathe/projects/agentic-harness/tools/dup_report.py`, `/home/user/lathe/projects/agentic-harness/qa/{pristine_gate,stale_gate,resource_dups_gate}.py`, `/home/user/lathe/projects/agentic-harness/tools/workflows.py`, `/home/user/lathe/docs/OPERATING_CONTRACT_DESIGN.md` (item 17).