# Workflow Reference — Fable edition vs Harness edition: what's the same, what's different

*Two independent accounts of the same 21 workflows: `WORKFLOW_REFERENCE.md` (Fable — hand-authored from the
source) and `WORKFLOW_REFERENCE_HARNESS.md` (the harness's own `lathe flow` output, verbatim). This is the
diff, and what it says about how self-documenting Lathe actually is.*

## The headline
Both agree completely on **what steps each workflow runs** — because both ultimately derive from the same
data (`tools/workflows.py`). They diverge entirely on **what those steps mean**: the harness emits the
*skeleton* (steps + a contract for 6 workflows); everything that makes the skeleton *usable* — which gates
fire, which personas, what to tune, what you get at the end — exists **only** in the hand-authored edition.

## Same in both

| | Detail |
|---|---|
| **Coverage** | Identical 21 workflows (6 named end-to-end + 15 per-invocation). |
| **Step sequences** | Same ordered steps for every workflow, with the same `AUTO`/`GATE`/`YOU` typing and the same `lathe` command per AUTO step. (The Fable edition read them from `workflows.py`; the harness prints them from the same dict — they cannot disagree.) |
| **Contracts** | The `when / entry / deliverable / done` for the six named workflows is the same text in both (both come from `CONTRACTS`). |
| **Invocation** | Both state `lathe flow <name> [--run <targets>]`. |

## Different

| Dimension | Harness edition (B) | Fable edition (A) |
|---|---|---|
| **Depth** | Step *labels* + the `lathe` command only. | Adds, per step: **which gate fires**, **which personas**, the **expected output**, and the **end-state artifact**. |
| **Gates** | Named only where a step literally says "gate". | Maps each GATE/build step to the actual gates (the 10-gate standing suite; the 7 STRICT rigor gates; RTM; assumption). |
| **Personas** | Not mentioned (except the step label "decider picks personas"). | Explains the decider (UCB1, default-on), that picks are dynamic, and how `LATHE_THINK` scales them. |
| **Configuration** | None. | A dials table (`LATHE_THINK`, `LATHE_STRICT`, `LATHE_PERSONA_UCB`, `LATHE_SPINE`, gate vars) + per-workflow tuning notes. |
| **The operating contract / spine** | Not explained — the harness prints per-flow, never the meta-story of how a **bare command routes through** its workflow + the six phases + the manifest. | A whole section (§0.2) + the `CONTRACT_FOR` flag table. |
| **What you get** | The `deliverable` line (6 workflows); nothing for the 15 per-invocation ones. | §3: the manifest, pins, `decisions.md`, `CLARIFIED_GOAL.md`, the trace matrix — the concrete artifacts. |
| **Honesty** | None. | §4 known caveats (the capstone findings, mostly fixed in v2.17–2.18) + an explicit "to be verified by live test." |
| **Grouping** | Flat, alphabetical flow dumps. | Grouped (named end-to-end vs per-invocation) with an explanation of the difference. |

## The trade the diff exposes

- **The harness edition cannot be wrong about *steps*.** It is the code's own output — regenerate it any time
  (`lathe flow`) and it never drifts. That is a genuine strength of workflows-as-data: the *what-happens* is
  machine-truthful and auditable by construction.
- **The harness edition is silent on *meaning*.** Gates-per-step, personas, config, outcomes — none of it is
  emitted. A user reading only the harness edition knows the sequence but not what to expect or how to tune it.
- **The Fable edition supplies the meaning but is *interpretation*.** Its "which gates fire / what you get"
  claims are read from the surrounding code, not emitted by the workflow itself — so they are exactly the
  claims the upcoming **live-test pass** must verify. Where A and the running system disagree, A is wrong (or
  the system is broken) — that is the test.

## What this says about the project (the meta-finding)
Lathe is **self-documenting at the step level and not at the semantic level.** The trust story ("you can see
exactly how the harness handles a job before running it") is *half true*: you can see the steps, not their
consequences. Two ways to close the gap, both worth considering after the test pass:
1. **Enrich `lathe flow`** to emit, per step, the gate(s) it triggers and the artifact it produces — then the
   harness edition would carry the meaning too, and the Fable edition could shrink to prose commentary.
2. **Keep the Fable edition as the human layer** but put it under the docs-drift discipline so it can't drift
   from `workflows.py`.

## Verdict
- **Most trustworthy for *what runs*:** the **Harness edition** (it is the source).
- **Most useful for *understanding and operating*:** the **Fable edition** (but pending live verification).
- **Best outcome:** the two should converge — the harness should emit more, and the human layer should be
  drift-gated — so there is one account that is both truthful and complete.

*Next: the live-test pass runs each workflow and checks it against the Fable edition's claims — that is where
we find out whether "what it says" equals "what it does."*
