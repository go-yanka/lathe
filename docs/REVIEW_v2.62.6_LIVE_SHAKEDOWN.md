# Lathe v2.62.6 — Live Terminal Shakedown (10 projects + all flows)

**Method:** drove the harness live through the CLI — Claude as analyst (opus) + implementer (sonnet), and **Gemini** as an alternate analyst (bring-your-own-brain) via a local shim. Built 10 diverse projects, then exercised every headline flow (brainstorm, SDLC, enhancement, bug-fix, review, verify, MCP, autonomy). All builds ran in an out-of-repo workspace.

## Capability coverage — all verified working
| Capability | Command | Result |
|---|---|---|
| build (goal → gated) | `do` | **8/10** gated-green (image/audio/voice/text/web) |
| brainstorm | `clarify` (run on **Gemini**) | ✓ 7-question interrogation + `CLARIFIED_GOAL.md` |
| requirements / SDLC | `sdlc` | ✓ RTM gate PASS, **17 traced items**, `REQUIREMENTS.md`+`rtm.json` |
| enhancement | edit plan + `build` | ✓ maze +`remove_wall` → **5 pins reused + 1 new** |
| bug-fix | sharpen spec + `build` | ✓ palette `hex_to_rgb` → **4 reused + refix**, verified |
| code / project review | `review auto` | ✓ found real bugs in *green* code (see meta-finding) |
| reproducibility | `verify` | ✓ byte-stable pin reuse |
| MCP server | `lathe_mcp.py` (stdio) | ✓ 5 tools, `lathe_verify` e2e (serverInfo **2.1.1**, stale) |
| autonomy | `auto` | ✓ loop + commit-gate honored (`LATHE_AUTO_COMMIT` off → uncommitted) |
| bring-your-own-brain | analyst = Gemini via shim | ✓ (requires a shim — see ISSUE-1) |

## Headline: META-FINDING — "gated-green" ≠ bug-free
`lathe review auto` over the **green** generated modules found HIGH bugs the build's own tests never covered:
- **csv_type_infer:** `split_simple_csv_line` ignores quoting (`1,"Smith, John",true` shredded); `zip_record` silently truncates length-mismatched rows + collapses duplicate headers; `infer_scalar` destroys leading zeros (`'007'`→7 — ZIP/phone corruption) and coerces `nan`/`inf`/`1_000`/unicode digits.
- **color_palette:** 3-digit `#fff` shorthand crashes all parsers (`int('',16)`); `rgb_to_hex` doesn't clamp (negative/overflow → malformed hex); 8-digit RGBA silently truncated.

**Implication:** "green" = "passes the tests the *analyst* wrote," and the analyst systematically under-covers malformed/boundary input. The **review step catches these** (working as designed) — but a plain `do` build **ships them**. Recommendation: default specs should include malformed/boundary tests, or `review` should run inside `do`.

## Issue list
| # | Sev | Finding |
|---|---|---|
| META | **HIGH** | gated-green ≠ bug-free — analyst under-tests edge cases (above) |
| 4 | MED | functional-lane: analyst mis-picks `web_canvas_game` (animation-required) for an **input-driven** canvas → a freehand drawing app false-fails 3× and the implementer bolts on fake auto-animation. Drafter prompt (`autonomy_live.py:160-180`) says prefer `behavioral`, but the analyst chose the liveness fallback. |
| 1 | MED | bring-your-own-brain: `request_spec.py:99` sends only `Content-Type` — **no auth header**, so "point at your own API key" needs a local key-injecting proxy. |
| 6 | MED | generated `color_palette.hex_to_rgb` accepts over-length hex (`#1234567`→`#123456`) silently (fixed live via the bug-fix flow). |
| 5 | MED | web build 09 (particle animation) hard-failed 3× on `functional:inline` — over-strict inline assert or genuine build difficulty. |
| 2 | LOW | `clarify` option parser mis-splits an option with a comma inside parens (`"Web browser (desktop, mobile)"` → two options). |
| 3 | LOW | `clarify` doesn't write `CLARIFIED_GOAL.md` when stdin EOFs before all questions answered (writes fine with enough answers). |
| 7 | LOW | non-descriptive / near-colliding workspace names (maze & palette both `python-module-generates_local_<stamp>`). |
| — | LOW | MCP `serverInfo.version` = `2.1.1` (stale vs repo `2.62.6`). |

## Notes
- 8/10 builds green; the 2 failures were both web (08 = ISSUE-4 misclassification false-fail; 09 = ISSUE-5 hard-fail). Function-lane (7/7) all green.
- Positive: the harness's **own review is strong** — it independently found the real generated-code bugs. Reproducibility, pin-reuse, RTM gating, commit-gating, and the INOPERATIVE tri-state all behaved correctly.
