# Vendoring Lathe — one canonical source, pinned consumers

This is the **complete, hardened, portable canonical Lathe** (see `VERSION`): all modules, all gates, the
dedup/registry/pristine cleanliness suite, and the resume-on-signal capability — fully integrated, 12/12
selftest, passes its own 4 cleanliness gates, uses **relative paths** so it builds on any install.

This tree is the single source of truth; pinned releases are cut from it. Projects **vendor** a copy —
they do **not** fork.

## The rule: VENDOR, DON'T FORK
- **One canonical** (this) holds all hardening + capabilities. Fixes/features land here.
- **Each project pins a tested copy.** Your churn can't break others; canonical churn can't break you.
- **Update deliberately:** on a new release, re-copy → run the checks → adopt only when green.
- **Project code stays in your project** (your plans, product gates, wrappers).
- **Reusable, general improvements flow BACK into canonical** (e.g. a JS gate), so every project benefits.

## How to vendor (drop-in)
1. Back up your current Lathe core (engine + the `agentic-harness` dir), then stop using it.
2. Copy from here into your project root: `engine_v2.py`, `lathe.py`, the `*.md` docs, and the whole
   `projects\agentic-harness\` (all 124 tool modules, all plans, the 5 gates, capabilities.json, a clean
   empty board).
3. Keep your own product layer untouched (your `projects/<your-product>/` tree — plans, product gates, wrappers).
4. Verify on YOUR machine: `python lathe.py gate` (all gates pass) and `python lathe.py selftest`
   (all green; needs your implementer + analyst endpoints up).
5. Dry-run your existing plans against the stricter validator (literal dicts, string-literal tests,
   identifier names, no f-strings in exec'd fields, import allowlist, >=1 test/function). Update any that
   fail or let the repair loop fix them.

## Keeping it pristine (intrinsic, no git needed)
`python lathe.py clean` quarantines corrupt/half-written files; the 4 gates fail a build on backup-named
files, duplicate DBs/resources, >1 `live` impl per capability, or any corrupt file. `lathe whatis <cap>` is
the source-of-truth lookup; `lathe dups` reports duplicate logic. Cleanliness is enforced, not git-dependent.

## Integrity
`MANIFEST.sha256` lists every shipped file with a checksum — verify a vendored copy matches this release.

## Excluded (ephemeral runtime state only — NOT code)
No live `harness.db` (a clean empty board ships instead), `RUN_REPORT.md`, `_fn_fails/`, `_archive/`,
`__pycache__/`, or session scratch logs. Everything that IS the harness is included.

## Read-only model (important)
The canonical (`C:\lathe-canonical`) is protected by a **directory ACL** so a stray build can't mutate it.
That ACL does **not** travel with copies — so **your vendored copy is fully writable** and builds normally.
(If you vendored an earlier 2026-06-30/30b release whose files came across read-only, clear it once:
PowerShell `Get-ChildItem <your-agentic-harness> -Recurse -File | %{$_.IsReadOnly=$false}`, then re-run selftest.)
