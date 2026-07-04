# Clarified goal (requirements liaison)

> Original: Redesign the persona subsystem (issue #9): a durable usage ledger of every persona invocation; explore/exploit selection so all 143 personas become reachable (not just ~44 today); work-based grades earned from findings that survive independent verification with a cold-start prior; auto and interactive selection modes; and a per-run manifest of who was considered, picked, and what each contributed. Backwards-compatible at every stage.

The answers are all blank — I can't synthesize a concrete brief without them. Below is a **provisional brief built on fallback assumptions**; correct any that are wrong and I'll tighten it.

---

**Refined goal:** Build a durable, explore/exploit-driven persona selection subsystem that makes all 143 personas reachable, grades contributions via independently-verified work evidence, and emits a per-run manifest — while remaining backwards-compatible with the existing invocation API.

---

**Assumptions** *(fallbacks — flag any that are wrong)*

- **Grade unit:** a scalar score per finding (e.g. 0–1 float), averaged across verified findings; "better" = higher average on findings that a second independent pass (cold-start, no prior context) also rates as valid.
- **Verification:** a second persona/agent run is seeded with only the raw task + finding, no prior conversation; if it independently arrives at the same conclusion, the grade sticks; otherwise the finding is quarantined.
- **Ledger:** a flat append-only JSONL file local to the project (one record per invocation); scope = per-project, not global.
- **Explore/exploit:** ε-greedy or UCB1 over the 143 personas; personas with no ledger entry are treated as "unseen" and get elevated explore probability until a minimum sample threshold is reached.
- **Interactive mode:** at invocation time, the user sees a ranked short-list (e.g. top 5 by grade + 1–2 explore picks) and picks one or accepts the auto-selected top choice.
- **Backwards-compat scope:** existing callers that pass a persona name directly continue to work unchanged; the new selector is only invoked when no explicit persona is specified.

---

**Constraints**

- Ledger writes must be atomic (no partial records on crash).
- Cold-start verifier must not read the ledger or any prior conversation — isolation enforced by API, not convention.
- No breaking changes to the existing persona invocation call signature.
- Grades must be reproducible: same inputs → same grade calculation.

---

**Acceptance criteria** *(each testable)*

1. After N invocations, every persona in the 143-set has been selected at least once for sufficiently large N (explore coverage test).
2. A persona invoked with an explicit name bypasses the selector and is recorded in the manifest — existing callers produce identical outputs.
3. A finding that the cold-start verifier rejects is never reflected in the grade average (quarantine gate test).
4. The per-run manifest lists: personas considered, persona selected, grade at selection time, finding summary, verification outcome.
5. Killing the process mid-write leaves the ledger in a valid state (no corrupt records).
6. Interactive mode presents ≥1 unseen persona in every short-list until all 143 have been explored.

---

**Non-goals**

- Global/cross-project ledger sharing.
- Real-time grade updates during a run (grades are committed post-verification only).
- UI beyond CLI/manifest output.
- Changing how personas are fetched or licensed.

---

**Open questions** *(must be answered before design begins)*

1. **Verification trigger:** does every finding get verified, or only findings above a confidence threshold? (Cost vs. coverage tradeoff.)
2. **Ledger scope:** per-project file confirmed, or does a team-shared remote store enter scope?
3. **Explore probability:** hard-coded ε / UCB constant, or configurable per project?
4. **Interactive mode surface:** CLI prompt inline, or a separate pre-run selection step?
5. **Grade decay:** do old grades expire / decay, or are they permanent?

---

Fill in the blanks above (especially the five open questions) and I'll produce a final, test-ready brief.

## Unstated assumptions (adversarial auditor — confirm the HIGH ones)
- **[high | data]** A "finding" is a discrete, atomic unit emitted by a persona run that can be independently re-evaluated — the goal mentions "findings" but never defines what constitutes one versus a raw response, a summary, or a judgment call.
- **[high | behavior]** Cold-start verification is implemented as a second persona/agent run against the same system, doubling inference cost per verified finding — the goal said "independent verification" but left the mechanism open (could be a fixed judge model, human review, or a rules-based check). [options: second persona run | dedicated judge model | human-in-loop | rules gate]
- **[high | behavior]** "Arrives at the same conclusion" in the verifier is a binary pass/fail — no similarity metric, threshold, or partial-credit model is defined, yet this single gate determines whether a grade is committed or a finding is quarantined.
- **[high | behavior]** Every finding is verified regardless of confidence — the brief lists verification trigger as Open Question #1 but the design includes no threshold gate, silently defaulting to verify-all; at scale this is a 2x cost multiplier with no escape valve.
- **[high | behavior]** Quarantined findings are permanently excluded from grade calculation with no re-evaluation path — the goal said findings "survive verification" but never said failed findings are dead; a re-queue or manual-override path was a live option.
- **[high | scope]** Ledger scope is per-project — the brief lists this as Open Question #2 but the constraint section and JSONL design pre-answer it, meaning a team-shared store would require a full persistence-layer replacement.
- **[high | data]** The 143-persona set is static for the life of a project; no protocol exists for adding personas mid-project, and the explore-coverage acceptance criterion (AC #1) would need reinterpretation if the set grows.
- **[high | interfaces]** Cold-start isolation is "enforced by API" — but the specific mechanism (separate API call with no injected context? system prompt that strips history? separate process?) is unspecified; if it reduces to a convention the isolation guarantee is hollow.
- **[med | behavior]** Grade is a simple arithmetic mean across verified findings — no weighting by recency, task complexity, or confidence level; a persona's first-ever poor result carries the same weight as its hundredth finding indefinitely. [options: simple mean | recency-weighted mean | Bayesian posterior | sliding-window mean]
- **[med | behavior]** Grades never decay — the brief lists decay as Open Question #5 but the design has no decay mechanism, implicitly treating all ledger history as equally relevant regardless of age.
- **[med | data]** The minimum sample threshold before a persona exits "elevated explore probability" is undefined — the design references it as a concept but sets no value; too low produces grade noise that drives selection; too high means the explore phase never practically ends.
- **[med | interfaces]** The per-run manifest is a separate artifact (file or structured output) distinct from the ledger — the goal said "emits a manifest" but the storage medium (file, stdout, appended JSONL record, sidecar) is unresolved, and programmatic consumers depend on this choice.
- **[med | interfaces]** Atomicity is guaranteed by an unspecified write mechanism — the constraint says "no partial records on crash" but names no implementation (write-then-rename, SQLite WAL, advisory file lock, etc.); on Windows the rename-over-existing semantics differ from POSIX and silently violate the guarantee if the wrong pattern is used.
- **[med | behavior]** The explore algorithm is ε-greedy or UCB1 — these have materially different convergence rates and exploration guarantees; ε-greedy with a fixed ε never fully stops exploring even after all 143 are well-sampled, while UCB1 self-tunes; the choice is deferred but baked into the selector's mathematical contract.

