# Redesign the persona subsystem (issue #9): a durable usage l — Requirements (layered, ID-traced)

Chain: UC -> BR -> FR -> TS, enforced by the RTM gate (no orphans, no dangling refs).

## Business use cases (UC)

| ID | Text | Traces to |
|---|---|---|
| **UC-1** | The orchestrator selects and dispatches personas across successive review runs so that all 143 personas become reachable over time through a principled explore/exploit policy. | — |
| **UC-2** | Findings produced by a persona are independently verified with a cold-start prior, a numeric grade is assigned, and that grade is persisted so future selection weights reflect demonstrated quality. | — |
| **UC-3** | A user inspects which personas were considered, selected, and contributed findings for any given run, and may override selection interactively before a run starts. | — |
| **UC-4** | An existing Lathe deployment upgrades to the new persona subsystem without breaking current persona definitions, invocation call sites, or in-flight run outputs. | — |

## Business requirements (BR)

| ID | Text | Traces to |
|---|---|---|
| **BR-1** | Every persona invocation must be durably recorded in a ledger that survives process crash, so selection history is never lost. | UC-1 |
| **BR-2** | The selection algorithm must balance exploration of rarely-used or never-used personas with exploitation of high-grade performers, guaranteeing all 143 personas are eventually reachable. | UC-1 |
| **BR-3** | Grades must be derived from findings that pass verification by an independent verifier that has no access to the originating run's context (cold-start prior). | UC-2 |
| **BR-4** | Verified grades must be written back to the ledger and must be the sole source used to update each persona's exploitation weight. | UC-2 |
| **BR-5** | The subsystem must support both an auto mode (no user interaction, config-driven N) and an interactive mode (user reviews candidates and may accept, reject, or add personas before the run starts). | UC-3 |
| **BR-6** | Each run must emit a manifest that records which personas were considered, which were selected, and which contributed at least one verified finding. | UC-3 |
| **BR-7** | All existing persona definition schemas and public invocation call signatures must remain valid and produce equivalent behavior after the upgrade. | UC-4 |

## Functional requirements (FR)

| ID | Text | Traces to |
|---|---|---|
| **FR-1** | On each invocation the ledger appends exactly one record containing: persona_id (string), run_id (string), timestamp_utc (ISO-8601), task_type (string), and status in {invoked, completed, errored}. | BR-1 |
| **FR-2** | Ledger writes use atomic write-then-rename so any read of the ledger file yields either the fully committed prior state or the fully committed new state; no partial record is ever visible. | BR-1 |
| **FR-3** | The selector computes a UCB1 score for each of the 143 personas using per-persona invocation count and cumulative mean verified grade stored in the ledger. | BR-2 |
| **FR-4** | Any persona with zero ledger entries receives an exploration bonus score of +infinity, placing it above all personas with at least one entry when the exploration budget is positive. | BR-2 |
| **FR-5** | The verifier receives only the finding text and task description; it has no access to the originating run's system prompt, conversation history, or tool outputs. | BR-3 |
| **FR-6** | The verifier returns a structured result {pass: bool, confidence: float [0.0, 1.0]}; the pipeline writes a grade only when pass=true, and discards the result when pass=false. | BR-3 |
| **FR-7** | After a finding passes verification, grade=confidence is written to the ledger entry keyed by (run_id, persona_id, finding_id); the entry is immutable once written. | BR-4 |
| **FR-8** | The UCB1 exploitation term for each persona is the arithmetic mean of all verified grades recorded in the ledger for that persona; the exploration term is sqrt(2 * ln(total_invocations) / persona_invocation_count). | BR-4 |
| **FR-9** | In auto mode the selector reads config key persona_selection.n (default 3), selects exactly n personas by descending UCB1 score, emits no interactive prompts, and returns the selection list within 500 ms excluding any model calls. | BR-5 |
| **FR-10** | In interactive mode the selector renders a ranked candidate list (minimum 5 entries) with persona name and UCB1 score, then accepts the commands reject <index>, add <persona_id>, and confirm; confirm freezes selection and proceeds. | BR-5 |
| **FR-11** | At run start the subsystem writes {run_id, timestamp_utc, considered: [persona_id,...], selected: [persona_id,...]} to {run_output_dir}/manifest.json; at run end it appends contributed: [persona_id,...] in-place. | BR-6 |
| **FR-12** | The contributed list in the manifest contains only those persona_ids that produced at least one finding with pass=true from the verifier during that run. | BR-6 |
| **FR-13** | A persona definition that contains only the legacy fields {name, description, system_prompt} loads without error; the loader injects default values grade=null and invocation_count=0 for the new fields. | BR-7 |
| **FR-14** | The existing invoke_persona(name: str) call signature is preserved; internally it resolves name to the ledger-aware path, records the invocation, and returns a result object whose schema is a strict superset of the pre-upgrade schema. | BR-7 |

## Technical specifications (TS)

| ID | Text | Traces to |
|---|---|---|
| **TS-1** | GIVEN a run that invokes persona P, WHEN the run completes, THEN the ledger contains exactly one record where persona_id=P.id, run_id matches the run, timestamp is a valid ISO-8601 string, and status is 'completed'. | FR-1 |
| **TS-2** | GIVEN a simulated process kill (SIGKILL) injected at a random byte offset during a ledger write, WHEN the ledger file is re-read, THEN it parses as valid JSON equal to either the pre-write snapshot or the fully-written post-write snapshot; no test run produces a third parse result. | FR-2 |
| **TS-3** | GIVEN a ledger seeded with heterogeneous invocation counts across all 143 personas, WHEN UCB1 scores are computed, THEN all 143 personas receive a finite score, the persona with the lowest invocation count ranks above the persona with the highest invocation count and equal mean grade, and re-seeding with updated counts produces a different ranking. | FR-3 |
| **TS-4** | GIVEN persona A has zero ledger entries and persona B has 10 entries with mean_grade=1.0, WHEN the selector runs with exploration_budget > 0, THEN A is always ranked first; GIVEN exploration_budget=0, THEN B is ranked first. | FR-4 |
| **TS-5** | GIVEN a finding F produced in run R whose system prompt contains the sentinel string 'ORIGIN_RUN_MARKER', WHEN the verifier is invoked on F, THEN the verifier's input messages contain no string matching 'ORIGIN_RUN_MARKER' and its context window shows no messages from R. | FR-5 |
| **TS-6** | GIVEN verifier returns {pass: false, confidence: 0.9}, THEN no grade record is written to the ledger for that finding; GIVEN verifier returns {pass: true, confidence: 0.75}, THEN exactly one grade record exists in the ledger with value 0.75. | FR-6 |
| **TS-7** | GIVEN a grade record written for (run_id='R1', persona_id='P1', finding_id='F1') with confidence=0.82, WHEN the ledger is queried for that triple, THEN grade==0.82; WHEN a second write is attempted for the same triple, THEN the write is rejected and the stored value remains 0.82. | FR-7 |
| **TS-8** | GIVEN persona P has invocation_count=5, mean_verified_grade=0.60, and total_invocations_across_all_personas=50, WHEN UCB1(P) is computed, THEN the result equals 0.60 + sqrt(2 * ln(50) / 5) within floating-point tolerance of 1e-9. | FR-8 |
| **TS-9** | GIVEN config persona_selection.n=3 and mode=auto, WHEN the selector runs, THEN it returns exactly 3 persona_ids, writes zero bytes to stdout before returning, and wall-clock time from call to return is less than 500 ms on a machine where ledger read takes less than 50 ms. | FR-9 |
| **TS-10** | GIVEN interactive mode is started, THEN stdout contains at least 5 lines each matching the pattern '<rank>. <persona_name> score=<float>'; GIVEN input 'reject 2', THEN the persona at rank 2 is removed from the candidate list; GIVEN input 'add persona_X', THEN persona_X appears in the list; GIVEN input 'confirm', THEN the selector returns immediately with the current list and accepts no further input. | FR-10 |
| **TS-11** | GIVEN a completed run with output directory D, THEN the file D/manifest.json exists, parses as valid JSON, and contains top-level keys run_id (string), timestamp_utc (ISO-8601 string), considered (array of strings), selected (array of strings), and contributed (array of strings). | FR-11 |
| **TS-12** | GIVEN persona P produced zero pass=true findings in run R, THEN P's id is absent from manifest.contributed; GIVEN persona Q produced exactly one pass=true finding, THEN Q's id appears exactly once in manifest.contributed. | FR-12 |
| **TS-13** | GIVEN a persona definition file containing only {name: 'legacy_persona', description: '...', system_prompt: '...'}, WHEN the loader parses it, THEN no exception is raised, the resulting object has grade==null and invocation_count==0, and the name/description/system_prompt values are unchanged. | FR-13 |
| **TS-14** | GIVEN a pre-upgrade call site that calls invoke_persona('legacy_persona') and captures the return value, WHEN the same call is made post-upgrade, THEN no exception is raised, the ledger contains one new invocation record for 'legacy_persona', and every key present in the pre-upgrade return object is present in the post-upgrade return object with the same type. | FR-14 |

## Suggested plan CRITERIA (each TS becomes an acceptance criterion)

```python
CRITERIA = [
    {'id': 'TS-1', 'text': "GIVEN a run that invokes persona P, WHEN the run completes, THEN the ledger contains exactly one record where persona_id=P.id, run_id matches the run, timestamp is a valid ISO-8601 string, and status is 'completed'.", 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-2', 'text': 'GIVEN a simulated process kill (SIGKILL) injected at a random byte offset during a ledger write, WHEN the ledger file is re-read, THEN it parses as valid JSON equal to either the pre-write snapshot or the fully-written post-write snapshot; no test run produces a third parse result.', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-3', 'text': 'GIVEN a ledger seeded with heterogeneous invocation counts across all 143 personas, WHEN UCB1 scores are computed, THEN all 143 personas receive a finite score, the persona with the lowest invocation count ranks above the persona with the highest invocation count and equal mean grade, and re-seeding with updated counts produces a different ranking.', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-4', 'text': 'GIVEN persona A has zero ledger entries and persona B has 10 entries with mean_grade=1.0, WHEN the selector runs with exploration_budget > 0, THEN A is always ranked first; GIVEN exploration_budget=0, THEN B is ranked first.', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-5', 'text': "GIVEN a finding F produced in run R whose system prompt contains the sentinel string 'ORIGIN_RUN_MARKER', WHEN the verifier is invoked on F, THEN the verifier's input messages contain no string matching 'ORIGIN_RUN_MARKER' and its context window shows no messages from R.", 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-6', 'text': 'GIVEN verifier returns {pass: false, confidence: 0.9}, THEN no grade record is written to the ledger for that finding; GIVEN verifier returns {pass: true, confidence: 0.75}, THEN exactly one grade record exists in the ledger with value 0.75.', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-7', 'text': "GIVEN a grade record written for (run_id='R1', persona_id='P1', finding_id='F1') with confidence=0.82, WHEN the ledger is queried for that triple, THEN grade==0.82; WHEN a second write is attempted for the same triple, THEN the write is rejected and the stored value remains 0.82.", 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-8', 'text': 'GIVEN persona P has invocation_count=5, mean_verified_grade=0.60, and total_invocations_across_all_personas=50, WHEN UCB1(P) is computed, THEN the result equals 0.60 + sqrt(2 * ln(50) / 5) within floating-point tolerance of 1e-9.', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-9', 'text': 'GIVEN config persona_selection.n=3 and mode=auto, WHEN the selector runs, THEN it returns exactly 3 persona_ids, writes zero bytes to stdout before returning, and wall-clock time from call to return is less than 500 ms on a machine where ledger read takes less than 50 ms.', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-10', 'text': "GIVEN interactive mode is started, THEN stdout contains at least 5 lines each matching the pattern '<rank>. <persona_name> score=<float>'; GIVEN input 'reject 2', THEN the persona at rank 2 is removed from the candidate list; GIVEN input 'add persona_X', THEN persona_X appears in the list; GIVEN input 'confirm', THEN the selector returns immediately with the current list and accepts no further input.", 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-11', 'text': 'GIVEN a completed run with output directory D, THEN the file D/manifest.json exists, parses as valid JSON, and contains top-level keys run_id (string), timestamp_utc (ISO-8601 string), considered (array of strings), selected (array of strings), and contributed (array of strings).', 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-12', 'text': "GIVEN persona P produced zero pass=true findings in run R, THEN P's id is absent from manifest.contributed; GIVEN persona Q produced exactly one pass=true finding, THEN Q's id appears exactly once in manifest.contributed.", 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-13', 'text': "GIVEN a persona definition file containing only {name: 'legacy_persona', description: '...', system_prompt: '...'}, WHEN the loader parses it, THEN no exception is raised, the resulting object has grade==null and invocation_count==0, and the name/description/system_prompt values are unchanged.", 'tests': ['<fn or fn:idx>']},
    {'id': 'TS-14', 'text': "GIVEN a pre-upgrade call site that calls invoke_persona('legacy_persona') and captures the return value, WHEN the same call is made post-upgrade, THEN no exception is raised, the ledger contains one new invocation record for 'legacy_persona', and every key present in the pre-upgrade return object is present in the post-upgrade return object with the same type.", 'tests': ['<fn or fn:idx>']},
]
```

Build under STRICT mode (`LATHE_STRICT=1`) so the chain is enforced end-to-end.