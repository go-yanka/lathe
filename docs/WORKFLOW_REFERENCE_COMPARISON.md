# Workflow Reference — Direct (Fable) vs Through-the-Harness: the contest

*Two accounts of the same 21 workflows, authored two ways, then compared honestly:*
- **Direct — `WORKFLOW_REFERENCE.md`:** Fable writing freely from the source, one pass.
- **Through the harness — `WORKFLOW_REFERENCE_HARNESS.md`:** a Fable-tier analyst **primed with the harness
  doctrine** (`CLAUDE.md`), forced to **ground every claim in `file:line`**, then run through the harness's
  **multi-lens self-review** (correctness / docs / adversarial) before shipping. The harness's *method*, not
  a data dump.
- (`WORKFLOW_REFERENCE_STEPS.md` — the raw `lathe flow` dump — is kept as the machine-truthful step index.)

*The hypothesis going in (owner's): the harness version should be better than the direct one. It is — and
here's the evidence, including where the direct version still wins.*

## Verdict first
**The through-the-harness edition is the better document.** It is more source-grounded, more complete, and —
decisively — its self-review **caught real defects the direct pass missed**, including an error in the direct
author's *own* earlier doc. This is a live demonstration of the harness thesis: the disciplined pipeline beat
the free single pass on the exact axis the project claims (verified > asserted).

## Same in both
- Identical **21 workflows** and identical **step sequences** (both derive from `workflows.py`; they cannot
  disagree on what runs).
- Same **contracts** (when/entry/deliverable/done) for the six named workflows.
- Both explain the operating-contract spine, the thinking dial, and the AUTO/GATE/YOU typing.

## Where the harness edition won

| Axis | Direct (Fable) | Through the harness |
|---|---|---|
| **Grounding** | Prose from the source; few explicit `file:line` cites. | `file:line` on nearly every claim (`workflows.py:34-44`, `spine_core.py:17`, `run_gates.py:24-33`…) — auditable. |
| **Completeness** | ~200 lines; the 15 per-invocation workflows compressed into a table. | ~357 lines; every workflow gets steps + gates-per-step + artifact, plus both gate families in full. |
| **Self-review** | None — single pass. | Three lenses run over its own draft; **6 concrete catches** folded in (below). |
| **Caught real defects** | No. | **Yes** — see the self-review payoff. |

### The self-review payoff (what the harness method caught that the direct pass did not)
1. **`GATES_REFERENCE.md` says 7 standing gates; the live runner has 10** (`run_gates.py:24-33` adds
   `manifest_contract`, `spine_enforced`, `gate_tristate`). A genuine docs-drift **in my own earlier doc** —
   the harness edition flagged it; my direct edition repeated "the 10-gate suite" without noticing the
   *reference* was stale. **→ actionable: fix `GATES_REFERENCE.md`.**
2. **`--think=high` emits `LATHE_ASSUMPTION_POLICY=high+med`** (`spine_core.py:17`) — a value *outside* the
   documented policy vocabulary (`off`/`high`/`med`/`all`). A latent quirk neither the direct doc nor I had
   spotted.
3. **There are TWO manifests** (`docs/ce/` spine manifest vs `agents/manifests/` persona manifest); "read the
   run manifest" is ambiguous. The direct edition said "the manifest" as if there were one.
4. The `front_end`/`select` contract flags are **metadata realized inside the primitives**, not separate
   spine calls — a more precise statement of the capstone's "decorative flags" finding.
5. Docs-lens: added a **bare-command column** so every per-invocation row is runnable.
6. Adversarial-lens: quoted the `workflows.py:21-23` rationale for why `code-review`'s rebuild is a YOU step
   (so it reads as intentional, not missing).

## Where the direct edition still holds an edge
Honesty cuts both ways:
- The direct edition carries a **`CONTRACT_FOR` flag table** and a **capstone-caveats section** tying the
  workflows to the just-fixed v2.16→2.18 findings — narrative context the harness edition trimmed.
- It is **more concise**; a reader who wants the shape fast may prefer it.
- Both are, on the *steps*, equally correct (shared source), so for "just tell me the sequence" the
  `STEPS` dump beats both.

## The meta-finding (this is the point)
This exercise is itself a test of Lathe's core claim. Same model tier, same source, two methods — and the
**structured method produced the more trustworthy artifact and surfaced defects the free pass missed**,
including a stale count in the reviewer's own prior documentation. That is exactly the value proposition:
*discipline beats a confident first draft.* The one caveat: the "harness" here reproduced the harness's
**method** (doctrine + grounding + multi-lens review) because the live analyst endpoint (`:8787`) was down;
a run through the real endpoint would be identical in method, potentially different in the specific model.

## Recommendation
1. **Adopt `WORKFLOW_REFERENCE_HARNESS.md` as the canonical workflow reference.**
2. Keep `WORKFLOW_REFERENCE_STEPS.md` (machine dump) as the always-current step index.
3. Keep `WORKFLOW_REFERENCE.md` (direct) as the narrative/context companion, or fold its `CONTRACT_FOR` table
   + caveats into the canonical.
4. **Act on catch #1:** update `GATES_REFERENCE.md` to 10 standing gates (the harness edition already found
   the drift).
5. Then run the **live per-workflow test** against the canonical edition's claims — the last verification.
