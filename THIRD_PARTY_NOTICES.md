# Third-Party Notices

Lathe (a spec-driven LLM code-generation harness) is distributed under the MIT
License. It incorporates and/or depends on the third-party components listed
below. Each is the property of its respective copyright holders and is used
under the terms of its stated license. SPDX license identifiers are provided
for clarity.

Lathe ships **no model weights**. See "Models (not bundled — user-provided)"
at the end of this file.

---

## Code dependencies

| Component | SPDX License | Used for |
|---|---|---|
| **Python** | `Python-2.0` (PSF License) | Engine, CLI, gates, and autonomy runtime — the language Lathe is written in. |
| **Ollama** | `MIT` | Default local model runtime for serving user-provided models. |
| **llama.cpp** | `MIT` | Alternative local serving (`llama-server`) for GGUF model weights. |
| **Playwright (Python)** | `Apache-2.0` | Drives a headless browser for behavioral UI gating (visual, performance, accessibility checks). |
| **Chromium** (bundled by Playwright) | `BSD-3-Clause` (plus its own third-party component licenses) | Headless browser engine used by Playwright. Browser binaries are fetched by the user via `playwright install`; they are not redistributed in Lathe. |
| **FastAPI** | `MIT` | Web framework for the OpenAI-compatible proxy shim (`claude_proxy.py`). |
| **Starlette** | `BSD-3-Clause` | ASGI toolkit underlying FastAPI. |
| **Pydantic** | `MIT` | Data validation and settings models for the proxy and config. |
| **uvicorn** | `BSD-3-Clause` | ASGI server hosting the proxy. |
| **bandit** | `Apache-2.0` | Static application security testing (SAST) for the security gate. |
| **axe-core** (vendored) | `MPL-2.0` | Accessibility (a11y) auditing for the accessibility gate. **See note below.** |
| **Pillow (PIL Fork)** | `HPND` (MIT-CMU / Historical Permission Notice and Disclaimer) | Pixel-level image diffing for the visual gate. |
| **SQLite** | Public Domain (`blessing` — SQLite Blessing) | Embedded database for the Kanban board and pins (via the Python stdlib `sqlite3` module). |
| **ruff** | `MIT` | Static lint gate (`qa/lint_gate.py`) — catches real bugs (undefined names, syntax, format) in generated code. Optional; the gate skips if absent. |
| **coverage.py** | `Apache-2.0` | Available for coverage checks (installed; used where a coverage gate is wired). |
| **universal-ctags** | `GPL-2.0` | External binary invoked as a subprocess for the multi-language code-structure map (`lathe map` / `tools/repomap.py`). **NOT linked or vendored — see note below.** Optional; the repo-map falls back to a stdlib-ast scan if absent. |
| **Compound-Engineering** (EveryInc) | `MIT` | Reviewer persona definitions **vendored** into `projects/agentic-harness/ce_personas/` and used by `lathe review` (`hreview.py`). See note below + `ce_personas/NOTICE.md`. |
| **Aider** (`aider-chat`) + **grep-ast** | `Apache-2.0` | External tools invoked by the benchmark (`benchmark/bench.py`) as a comparison baseline. Not part of the harness runtime; not redistributed. |
| **tree-sitter** + **tree-sitter-language-pack** | `MIT` | Transitive deps of grep-ast (benchmark only). Not used by the shipped repo-map (which uses ctags). |

---

## Note on axe-core (MPL-2.0 — file-level copyleft, vendored)

`axe-core` is licensed under the **Mozilla Public License 2.0 (`MPL-2.0`)**, a
weak, *file-level* copyleft license. Lathe **vendors** axe-core as a separate,
unmodified file rather than merging its source into Lathe's own MIT-licensed
files. Under MPL-2.0:

- The axe-core file(s) remain under MPL-2.0, and that license must be preserved
  alongside them.
- Any modifications to the axe-core source files themselves must be made
  available under MPL-2.0.
- MPL-2.0's copyleft is per-file: it does **not** extend to Lathe's own source
  files that merely call axe-core. Lathe's code stays MIT.

To stay compliant, keep axe-core as a clearly identified, standalone vendored
artifact with its MPL-2.0 license header/notice intact. Do not copy axe-core
source into MIT-licensed Lathe files.

Source: https://github.com/dequelabs/axe-core

---

## Note on Compound-Engineering personas (MIT — vendored)

`lathe review` (`hreview.py`) uses the **actual** Compound-Engineering reviewer persona definitions, vendored
unmodified into `projects/agentic-harness/ce_personas/` (with CE's `LICENSE` and a `NOTICE.md` recording the
source repo, version 3.17.0, and commit). CE is **MIT**, compatible with Lathe's MIT license; the vendored files
carry CE's license alongside them. We do **not** reimplement CE — we use its code. Refresh path is in
`ce_personas/NOTICE.md`. Source: https://github.com/EveryInc/compound-engineering-plugin

## Note on universal-ctags (GPL-2.0 — external tool, NOT linked or vendored)

The repo-map (`lathe map` / `tools/repomap.py`) **shells out to the `ctags` binary** as a separate process and
parses its JSON output. Lathe does **not** link against, statically include, or redistribute any ctags code or
binary — the user installs ctags themselves (e.g. `winget install UniversalCtags.Ctags`). Invoking a separate
GPL-2.0 program at arm's length ("mere aggregation") does **not** place Lathe's own MIT-licensed code under the
GPL. If ctags is absent, the repo-map falls back to a stdlib-`ast` scan, so ctags is an optional enhancement.
Source: https://github.com/universal-ctags/ctags

---

## Models (not bundled — user-provided)

**Lathe ships NO model weights.** It is model-agnostic: the user pulls a model
and accepts that model's terms. The licenses below are the *user's*
obligations, not Lathe's, and are listed for transparency only.

| Model | License | Notes |
|---|---|---|
| **Gemma** (Google) | Gemma Terms of Use | Commercial use permitted, but carries a Prohibited-Use Policy that passes through to downstream users. **Not** an OSI-approved license. Weights are user-pulled, not redistributed by Lathe. Source: https://ai.google.dev/gemma/terms |
| **Qwen2.5-Coder-32B-Instruct** (Alibaba/Qwen) | `Apache-2.0` | Verified Apache License 2.0 (this specific size/variant is Apache-licensed; some other Qwen sizes use the restricted "Qwen License" / "Tongyi Qianwen License", which does **not** apply here). Source: https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct/blob/main/LICENSE |
| **Ornith-1.0** (DeepReinforce AI; 9B dense and 35B MoE variants) | `MIT` | Verified MIT, with no regional restrictions. Both variants are post-trained on top of Gemma 4 and Qwen 3.5 (themselves Apache-2.0). Sources: https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B and https://huggingface.co/deepreinforce-ai/Ornith-1.0-9B |

The full text of each license referenced above is available from the
corresponding project's distribution.
