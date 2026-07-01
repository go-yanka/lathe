# License Compliance — pre-publication verification

**Date:** 2026-06-29. **Scope:** publishing the Agentic Harness as open source (and possibly commercial),
under Digicraftique.AI. Each dependency below was checked against **how we actually integrate it**, not
generic usage. This is a precise reading of license text + official terms, **not formal legal advice** — the
one RED item must get counsel / Anthropic sign-off before launch.

## The "high-brain" provider is PLUGGABLE — bring-your-own (resolves the only red item)

The harness's analyst/reviewer brain is **not hardcoded to our Claude**. The engine resolves it from
`HARNESS_CLAUDE_URL` (any OpenAI-compatible endpoint), exactly like the local implementer resolves from
`LOCAL_OPENAI_URL`. So the published harness is **brain-agnostic**: a user points it at whatever higher-power
model they have access to — their own Anthropic **API key** gateway, their own Claude CLI, or **any other
frontier model** (GPT/Gemini/etc.) behind an OpenAI-compatible endpoint. Their auth choice is their own
compliance, not ours.

The underlying Anthropic fact (for whoever uses *their* Claude this way): driving Claude Code programmatically
on a Pro/Max **subscription** is "ordinary use" for one's own work but **not** permitted for a third-party
product routing *other* users through subscription credentials — Anthropic directs developer products to
**API-key auth**. Implications for us:

- **We, internally**, on our own subscription, building our own projects = fine (ordinary use). `claude_proxy.py`
  (subscription → `claude -p`) stays as our INTERNAL default. No change to how we work.
- **What we SHIP** must not route others through any subscription. We ship the pluggable seam + a default of
  **bring-your-own** (`HARNESS_CLAUDE_URL` = your API-key gateway / your CLI / your frontier model). We bundle
  no Anthropic code and route nobody through our credentials. Document API-key as the recommended path.

Net: already supported in code (env-configurable). This is a **default-config + docs** task, not a redesign.
Source: https://code.claude.com/docs/en/legal-and-compliance · https://www.anthropic.com/legal/commercial-terms

## Compliance table

| Dependency | Integration | License | Permitted | Obligations | Risk |
|---|---|---|---|---|---|
| llama.cpp | separate process, HTTP, no linking | MIT | yes | none run-only; if we ship binaries: LICENSE + © notice | 🟢 |
| Ollama | separate process, HTTP | MIT | yes | none run-only; if we ship binaries: LICENSE + scan bundled Apache-2.0 components | 🟢 (🟡 if shipping binary) |
| **Claude Code CLI** | `claude -p` subprocess; capture text | Proprietary (all rights reserved) | **outputs yes; subscription automation NO** | **switch shipped tool to per-user API keys**; never bundle the CLI | 🔴 → 🟢 with API keys |
| compound-engineering plugin (ce-* personas) | reference persona *names* in prompts; user installs plugin | MIT (© 2025 Every) | yes | none (we copy no files); don't brand as "Compound Engineering" | 🟢 |
| Playwright | dev/test only, pip, not bundled | Apache-2.0 | yes | none (dev-only); only if bundled: ship license text | 🟢 |
| axe-core | inject **unmodified** at test time | MPL-2.0 | yes | MPL is file-level copyleft → unmodified use = **no source-disclosure**; if we *vendor* axe.min.js keep its LICENSE + in-file notice; don't use AXE® mark | 🟢 |
| Bandit | dev SAST, pip | Apache-2.0 | yes | none (dev-only) | 🟢 |
| Pillow | visual-diff, pip | **MIT-CMU** (not HPND) | yes | none (dev-only); if bundled: 3 © lines + name-use restriction | 🟢 |
| Gemma weights | documented/recommended; **no weights shipped** | Gemma 1–3 custom Terms; **Gemma 4 Apache-2.0** | yes | none for recommending (documenting ≠ distribution) | 🟢 |
| Qwen2.5-Coder weights | documented; no weights shipped | 7/14/32B Apache-2.0; **3B = Qwen Research (non-commercial)** | yes | README must flag 3B non-commercial; recommend 7B+ for commercial | 🟢 (🟡 README) |
| Ornith-1.0-35B weights | documented; no weights shipped | declares MIT; base lineage unverified | yes | none for recommending; redistributors must verify base-model license | 🟢 (🟡 if redistributed) |

## Pre-release checklist

**Blocking:**
1. Switch the shipped Claude integration to **per-user API-key auth**. Do NOT ship `claude -p` against a Pro/Max subscription. (If a subscription path is ever wanted, get written Anthropic confirmation first.)

**NOTICE / attribution (only for what we actually ship):**
2. Redistribute llama.cpp binaries → MIT text + `© 2023–2026 The ggml authors`.
3. Redistribute Ollama binaries → MIT text + `© Ollama` + scan the binary's bundled Apache-2.0 components.
4. Vendor `axe.min.js` in the repo → keep upstream MPL-2.0 LICENSE (Exhibits A/B) + in-file banner + link to pinned upstream source. (Fetch-at-runtime, never committed → no obligation.)
5. Playwright / Bandit / Pillow as pure dev deps not bundled → **no NOTICE entry required**.

**README accuracy (protects users):**
6. Qwen2.5-Coder: 7B/14B/32B Apache-2.0 (commercial-OK); **3B non-commercial**.
7. Ornith-35B: MIT declared; redistributors verify base-model (Gemma 4 / Qwen 3.5) inheritance.
8. Gemma: 1–3 custom Terms; 4 Apache-2.0.

**Avoid:**
9. Don't bundle/redistribute the Claude Code CLI or any Anthropic code.
10. Don't centralize one subscription for many users; don't share credentials.
11. Don't brand as "Compound Engineering" / "axe" / use the AXE® mark — nominative reference ("works with…") is fine.
12. Don't ship model weights (keeps us clear of every model license — stay model-agnostic).
13. Don't ship Playwright's downloaded browser binaries without handling their separate licenses.

**Net:** 9 of 10 dependencies are green; the model weights are clean because we ship none. The single real
blocker is the Claude subscription-auth path — fixed by per-user API keys, which Anthropic explicitly permits.
