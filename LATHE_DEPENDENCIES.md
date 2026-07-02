# Lathe — Dependencies & Legality

What Lathe uses, how, and whether it's safe to open‑source and ship. **Bottom line: the Lathe *code* is
MIT and every code dependency is permissive (MIT/BSD/Apache/MPL), so the tool is clean to release. The
only legal care is around *model weights* and the *premium brain* — both handled by Lathe's
model‑agnostic design (ship no weights; bring your own model + your own key).**

## Code dependencies

| Component | How Lathe uses it | License | Ship / OSS? |
|---|---|---|---|
| **Python 3.11+** | Engine, CLI, gates, autonomy — all of it | PSF (permissive) | ✅ |
| **Ollama** | Local model runtime (the published default path) | MIT | ✅ |
| **llama.cpp** | Alternative local serving (rig `llama-server`, the 35B/9B) | MIT | ✅ |
| **Playwright (Python)** + Chromium | Behavioral UI gating (H3 visual, H4 perf, H6 a11y) drive a headless browser | Apache‑2.0 (Chromium: BSD + its own bundle) | ✅ (browser binaries fetched by the user via `playwright install`) |
| **FastAPI / Starlette / Pydantic** | `claude_proxy.py` OpenAI‑compatible shim | MIT / BSD‑3 / MIT | ✅ |
| **uvicorn** | ASGI server for the proxy | BSD‑3 | ✅ |
| **bandit** | H5 security gate (SAST) | Apache‑2.0 | ✅ |
| **axe‑core** (vendored) | H6 accessibility gate | **MPL‑2.0** (file‑level copyleft) | ✅ with care — keep it a separate vendored file + attribution; don't merge axe source into MIT files |
| **Pillow (PIL)** | H3 pixel‑diff | MIT‑CMU/HPND | ✅ |
| **SQLite** (stdlib `sqlite3`) | Kanban board, pins | Public domain | ✅ |

All permissive → **Lathe can be MIT‑licensed and shipped** with a standard third‑party‑notices file
(attribution for axe‑core/MPL especially).

## Models — the one area that is NOT plain OSS

Model weights carry their own licenses, several with **use restrictions** (not OSI‑approved). Lathe's
stance (already in the README): **it ships NO weights and is model‑agnostic** — the user pulls a model
and accepts that model's terms. So these are the *user's* obligations, not Lathe's:

| Model (as used here) | Role | License | Note |
|---|---|---|---|
| **Gemma 4 12B** (published default local impl) | Local code generation | **Gemma Terms of Use** (Google) | Commercial use OK, but carries a Prohibited‑Use Policy that must pass through to downstream; **not OSI**. Don't redistribute weights — let users pull. |
| **Qwen2.5‑Coder‑32B‑Instruct** (rig codegen) | Local code generation | **Apache‑2.0** (verified — [LICENSE on HF](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct/blob/main/LICENSE)) | ✅ Clean. The restricted "Qwen/Tongyi Qianwen License" does NOT apply to this size — the 32B Coder is plain Apache‑2.0. |
| **Ornith‑1.0 (35B MoE / 9B)** (local implementer / agent brain) | Agentic / brain | **MIT** (verified — DeepReinforce AI; [35B](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B) / [9B](https://huggingface.co/deepreinforce-ai/Ornith-1.0-9B)) | ✅ Clean, no regional restrictions. Both variants post‑trained on top of Gemma 4 + Qwen 3.5 (each Apache‑2.0); the Ornith release itself is MIT. |
| **Claude** (via `claude_proxy.py`) | The "analyst" / premium thinking | Anthropic Commercial Terms | See below. |

## Two legality watch‑items (both already satisfied by design)

1. **Ship no model weights.** Gemma/Qwen/Ornith terms are the user's to accept on pull. Lathe stays
   model‑agnostic — "the thinking role can be a human or a local model" — so the tool itself carries no
   model license. ✅
2. **The premium brain must be bring‑your‑own per‑user key.** Anthropic's terms prohibit routing other
   users' requests through a Pro/Max subscription (`claude -p`). Internal/solo use is fine; a *hosted*
   Lathe offering must take each user's own API key. Because the analyst role is pluggable
   (`HARNESS_CLAUDE_URL` = any OpenAI‑compatible endpoint, or a local model, or a human), this is
   satisfied by design. ✅

## Prior art / honesty

`PRIOR_ART.md` already maps Lathe's ideas to existing work (Spec Kit, Kiro, Tessl, BMAD; Reflexion;
FrugalGPT/COPE; Aider/Cline/Cody; Ollama) and claims only the *combination* + three choices
(no‑escalation, content‑hash pinning, behavioral gating). Keep that file current on release.

## Action before public v2 release

- [ ] Confirm the exact **Qwen** variant license and the **Ornith** base‑model license (the two VERIFY rows).
- [ ] Add a `THIRD_PARTY_NOTICES.md` (attribution incl. axe‑core/MPL‑2.0).
- [ ] Keep the "ship no weights / BYO brain key" line prominent in the README.
