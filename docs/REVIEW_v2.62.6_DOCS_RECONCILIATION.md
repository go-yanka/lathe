# Lathe v2.62.6 — Code-vs-Docs Reconciliation & Fix List

**For:** the implementer/maintainer, to review and fix (primarily documentation, plus one code bug).
**Method:** two independent reviews of the entire codebase at v2.62.6 —
1. **Direct code review** (Mode 2): six subsystem inventories reading `lathe.py` (3002 lines), `engine_v2.py` (1863), all 120 `tools/` modules, 29 gates, and the 104 docs — every capability mapped to `file:line`.
2. **Through the harness** (Mode 1): live `lathe review` (real personas, analyst on opus) — `review auto` across the core + docs and `review all` (10 lenses) on the safety-critical files. *(The full sweep is still running; findings below marked ⟳ will be appended as they land. Everything unmarked is verified.)*

**Origin:** this started from an external LLM's "testing manifest" that made two wrong claims (`do` triggers `clarify`/emits `CLARIFIED_GOAL.md`; you "seed" `ADVOCATE.md`). Both trace to *ambiguous doc wording*, not to false docs — fixes #A1/#A2 below close them.

---

## A. Doc wording that misleads readers (the external-LLM confusions)

**A1 — `do` vs `clarify` conflation.** `README.md` §"Clarify before you build" places `lathe clarify` → `CLARIFIED_GOAL.md` and `lathe do`'s intake back-to-back under one heading, inviting readers to merge them.
- **Code truth:** `do` writes `GOAL.md` (`lathe.py:762`, via `workspace_docs`); `clarify` writes `CLARIFIED_GOAL.md` (`lathe.py:2385`). Separate commands, separate artifacts; `do` never emits `CLARIFIED_GOAL.md`.
- **Fix:** state explicitly that `clarify` is a *separate, optional* upstream command emitting `CLARIFIED_GOAL.md`, while `do` runs its *own* intake and writes **`GOAL.md`**.

**A2 — `ADVOCATE.md` reads like a user input.** `README.md:104` / `ARCHITECTURE.md:123`: *"Seeded with your goal … as a charter (written to `ADVOCATE.md`)."*
- **Code truth:** the harness **generates** the charter from the goal + discovery + assumptions and **overwrites** `ADVOCATE.md` every run (`advocate.py:37-56`; written `lathe.py:778-779`); it is never read back as input.
- **Fix:** reword to "the harness **generates** the charter **from** your goal and **writes** it to `ADVOCATE.md` (an output you read, **not** a file you author)."

---

## B. Doc numbers that are stale/wrong (verified against code)

| # | Doc claim | Code truth | Fix |
|---|---|---|---|
| B1 | **Standing gates:** README.md:156 "**Ten**"; GATES_REFERENCE.md:230-238 & CLI_REFERENCE.md:68 "**7**" | **28** standing (`run_gates.py` CHECKS; 25 per-build, 3 heavy behind `lathe gate`) | Fix to 28; **GATES_REFERENCE Part 2 is missing 18 gates** — add them |
| B2 | **STRICT rigor gates:** "**seven**" (multiple docs); LATHE_CAPABILITIES.md:43-51 lists an 8th (`LATHE_ADV_SYNTH`) | **8** forced gates (test-ack, regression-proof, spec-lint, mutation-score, glue, test-kind, assumption, RTM/traceability) + adv-synth default-on (`strict_mode.py`, `engine_v2.py:112-140`) | Reconcile to 8 + adv-synth |
| B3 | **Env vars:** 53 (LATHE_COMMANDS.md:249, GATES_REFERENCE.md:319) vs 66 (CLI_REFERENCE.md:369) | **88** in `env_catalog.py` (env-drift gate reports ~94 code-referenced) | Fix to current count in all three |
| B4 | **Version:** README.md:186 v2.61.0; CLI_REFERENCE.md v2.7.0; GATES_REFERENCE v2.9/2.12; LATHE_CAPABILITIES v2.61.0 | repo **v2.62.6** | Update version stamps |
| B5 | **`CLAUDE_TIMEOUT`:** 120 (LATHE_GUIDE.md:337) vs 600 (CLI_REFERENCE.md:168) | `request_spec` default 180s; proxy 600s — pick the authoritative one | Reconcile |
| B6 | **Python:** 3.10+ (README.md:29) vs 3.11+ (LATHE_GUIDE.md:41) | — | Reconcile to the real minimum |

---

## C. Doc-internal contradictions & omissions

- **C1 — `sdlc` scope:** LATHE_COMMANDS.md:414 = "authoring only → `REQUIREMENTS.md`"; CLI_REFERENCE.md:55 = "clarify→…→build→review in one command." **Code:** `cmd_sdlc` (`lathe.py:2392`) writes `REQUIREMENTS.md` + `rtm.json`, RTM-gates, runs an Advocate checkpoint — it is **authoring, not a full build**. Fix CLI_REFERENCE.md:55.
- **C2 — STRICT "explicit env wins" vs "clamps weaker up":** GATES_REFERENCE.md:29 says an explicit env var always wins; :333-339 says STRICT clamps a weaker preset *up*. **Code:** `strict_clamp` (`strict_mode.py`) **does** clamp weak values up — so "explicit env always wins" is wrong for weakenings. Fix to "stricter wins; weaker is clamped up."
- **C3 — workflow list:** README.md:63 lists **6**; LATHE_COMMANDS.md:94 lists **5** (omits `sdlc`). Code: 6 named. Fix LATHE_COMMANDS.
- **C4 — `logs` command** is live (`cmd_logs`, `lathe.py:1647`; dispatch `:2631`) but absent from the `lathe`/`help` usage block and the bare-command list. Add it. Same for `serve`/`map`/`checkin` (dispatched, missing from usage block).
- **C5 — `workflows.py:135` comment** claims a "19-id set" but only **15** per-invocation workflows are defined. Fix the comment (or add the missing 4).
- **C6 — `LATHE_REPAIR`** is referenced in LATHE_COMMANDS.md:151 and read at `lathe.py:195` but missing from CLI_REFERENCE's env tables. Add it.
- **C7 — MCP `serverInfo` version** = `2.1.1` (`lathe_mcp.py:87`), stale vs v2.62.6.

---

## D. Code bug (the one non-doc fix)

**D1 — [MEDIUM, safety] The Advocate can silently downgrade a VETO.**
`_extract_verdict_json` (`advocate.py:98-122`) keeps the **last** verdict-bearing object it finds ("prefer the last verdict-bearing object"). It is **not** strength-ranked, so a reply whose genuine `veto` precedes any trailing `{"verdict":"approve"}`-shaped object resolves to APPROVE — the exact "the strongest verdict is the one most easily lost" failure its own docstring frets about. Caught independently by the harness's `correctness` **and** `adversarial` lenses; confirmed by direct read.
- **Fix:** rank by strength (`veto` > `concern` > `approve`) among all verdict-bearing objects, or take the first, rather than the last.
- **Also (LOW, latent):** `_clip` duplicates content when `n` is small (`tail<=0` → `s[-tail:]` == whole string). Unreachable from current callers (n ∈ {2000,6000,12000}) but a trap.

---

## E. Wiring gaps (report-only — behavior vs. documented intent)

- **E1 — Persona grades run but are starved.** `update_grades`/`finding_score`/`grade_update` execute every run (`persona_orchestrator.py:170,176-211`), but live callers pass empty `contributions`/`raised`/`confirmed` (`persona_spawn.py:127`, `lathe.py:1020-1024`), so grades stay at the 0.5 prior — the *explore* (UCB1) machinery is real; the *exploit* signal is effectively inert. Docs imply "work-based grades"; reality is explore-mostly. Fix or document.
- **E2 — `review auto` is lexical, not semantic.** It uses a hardcoded keyword table (`lathe.py:979-985`); the semantic decider (`semantic_decider`, wired to the *intake* panel) is not used for `review auto`. Wire it, or state "keyword-match."
- **E3 — Dead code:** `persona_select.select_personas` (`persona_select.py:28-70`) is unused on any live path — the orchestrator reimplements ranking inline. Remove or wire.

---

## F. What's confirmed vs pending
- **Verified (A, B, C, D, E):** all grounded in the direct code read + the harness slice (advocate lenses).
- **⟳ Pending:** the comprehensive `review auto` (21 targets) + `review all` (3 files) sweep is still running; additional harness findings will be appended to this report as they land.

## G. Recommended split
- **Docs (implementer):** A1–A2, B1–B6, C1–C7.
- **Code (one PR):** D1 (Advocate verdict strength-rank) + D1-LOW (`_clip`).
- **Report to maintainer / triage:** E1–E3.

---

## H. Comprehensive harness sweep — additional findings (24 targets: `review auto` ×21 + `review all` ×3)

The full sweep completed. These are **harness-surfaced** (opus personas across all 10 lenses); the implementer should triage before fixing (the D1 Advocate one is already independently confirmed). Full logs retained.

### H.1 New CODE findings to verify + fix
- **[HIGH] `run_gates.py` retry masks intermittent *real* bugs.** The retry loop `break`s and reports PASS the instant *any* attempt returns 0. A gate catching a timing-dependent real bug ~1-in-3 is reported green ~87% of the time (`GATE_RETRIES=2`). It conflates "flake = false FAIL" with "intermittent real bug." **Fix:** for deterministic (non-HEAVY) gates require *all* attempts clean; scope any-pass retry to the browser/HEAVY set only.
- **[HIGH] `persona_select.py` float-count guard disables the bandit.** `ucb1`/`select_personas` use `isinstance(count, int)`, so float counts (JSON/pandas/np.int64) score `float('inf')` → every persona looks unexplored → selection degrades to a static **alphabetical** picker with no error (`grades` is `float()`-coerced but `counts` isn't). **Fix:** coerce numerically (`int(cnt)`, reject only bool) in both `ucb1` and the `total` loop. *(Note: `select_personas` is dead code per E3, but `ucb1` is live.)*
- **[MED→HIGH] Second Advocate VETO-downgrade path (compounds D1).** `checkpoint`'s anti-injection line-anchored strip `re.sub(r'(?im)^.*"verdict"...')` is **bypassed by a multi-line-embedded** `{"verdict":"approve"}`, which then wins via the last-object rule. So D1 has two doors, not one. **Fix D1 by strength-ranking** closes both.
- **[MED] `advocate.build_charter` robustness:** docstring "never raises on odd input" is violated on a non-iterable `assumptions`; the charter is derived data with **no stamp tying it to its inputs** (goal/discovery/assumptions); a VETO carrying an unrecognized route is silently stripped to `""`, stranding the route.
- **[MED] `persona_orchestrator.record_run` concurrency:** two concurrent runs corrupt the append-only `usage_ledger.jsonl` and race the `grades.json` tmp-file; `relevance_pool`/`select_live` select a duplicated persona name twice (double weight); the exploration term collapses to zero in a common degenerate pool.
- **[HIGH, maintainability] Duplicate module-loader.** The `spec_from_file_location…exec_module` dance is reimplemented in `_tool`, `_board`, `_load_autonomy`, and inlined in `cmd_serve`/`cmd_env`/`cmd_ack`/`cmd_assume`/`cmd_trace` (`lathe.py:124,1087,1289,+8`). `_board`==`_tool("board")`. **Fix:** delete `_board`/`_load_autonomy`, give `_tool` a `root=` param, route all sites through it.

### H.2 New DOC findings to fix (add to the §B/§C list)
- **LATHE_GUIDE.md:** `LOCAL_OPENAI_URL` default `:8089` vs every worked example `:8080`; `LATHE_MODEL` vs `HARNESS_MODEL` both described as the implementer model with conflicting defaults; `HARNESS_MODEL` name drifts (`gemma2`/`gemma4`/ollama pull); §5 "plans run in filename order = the dependency graph" **breaks at ≥10 plans** (lexicographic sort) with no zero-pad note.
- **CLI_REFERENCE.md:** `--out` marked optional in syntax but "required" in the flag table; `LATHE_RUN_TIMEOUT` default "unbounded" is a CI/`auto` hang risk; `LATHE_SANDBOX` default is environment-dependent (same command runs untrusted code at different isolation); undocumented precedence between `LATHE_VALIDATE_PLAN` (CLI-forced on) and `LATHE_TRUST_PLAN` (bypass).
- **PERSONAS.md:** the decider double-counts name overlap (generic multi-word names beat specialists); a zero-signal goal collapses to a 143-way tie returned as "defaults" (catalog order).
- **ARCHITECTURE.md:** persona-count arithmetic inconsistent ("143 = 12 vendored + …").
- **REPRODUCIBILITY.md / LATHE_CAPABILITIES.md:** the pin key `sha256(name+prompt+tests+model)` **omits `HEADER`/`GLUE`/`context`** — editing hand-authored glue changes the assembled module but not the key. REPRODUCIBILITY.md notes the boundary; make sure LATHE_CAPABILITIES states it too.
- **LATHE_COMMANDS.md:** duplicated "Scrutiny is user-governed" block under `lathe assume`.

### H.3 Meta
The two-mode split earned itself: **the harness sweep found real HIGH bugs the direct read missed** (the gate-retry masking, the float-count bandit degradation, the second Advocate injection path), while the direct read gave the exact `file:line` ground truth for the doc numbers. Neither alone was sufficient.
