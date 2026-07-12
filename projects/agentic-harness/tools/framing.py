"""framing.py (#48) — the project-FRAMING round for `lathe clarify`.

The intake interview asks the FUNCTIONAL questions (inputs/outputs/edge cases) but never the FRAMING questions
that actually determine the architecture and what "done" means — purpose, users, scope, deliverable form, tech
stack, hosting. Almost no AI coding tool asks these, which is exactly why they confidently build the wrong
SHAPE of thing. This module is the fixed question set + a conservative goal-prefill (skip a dimension the goal
already states, never guess) + the CLARIFIED_GOAL.md 'Framing' section renderer. The interactive asking lives in
cmd_clarify (shared interview_io). Pure + deterministic — no model, no I/O.
"""

# The six framing dimensions. `options` empty => free-text (stack). Order = ask order.
FRAMING = [
    {"key": "purpose", "question": "What's the purpose / motive of this?",
     "options": ["personal / hobby", "learning exercise", "throwaway prototype", "internal tool",
                 "open-source library", "a SaaS / product", "client deliverable"]},
    {"key": "users", "question": "Who will use it?",
     "options": ["just me", "my team", "external end-users", "other developers / an API consumer", "the public"]},
    {"key": "scope", "question": "How ambitious / long-lived is it?",
     "options": ["quick script", "an MVP", "production-ready", "a long-lived system"]},
    {"key": "deliverable", "question": "What FORM should the deliverable take?",
     "options": ["CLI tool", "library / package", "web app", "REST / GraphQL API", "desktop / mobile app",
                 "notebook / report", "data pipeline", "config / infra"]},
    {"key": "stack", "question": "Any tech-stack preferences (language, framework, datastore, key libraries)?",
     "options": []},
    {"key": "hosting", "question": "Where will it run / deploy?",
     "options": ["local only", "Docker", "a PaaS (Vercel / Fly / Render)", "a cloud (AWS / GCP / Azure)",
                 "self-hosted", "an app store", "npm / PyPI"]},
]

_LABELS = {"purpose": "Purpose", "users": "Users", "scope": "Scope", "deliverable": "Deliverable",
           "stack": "Tech stack", "hosting": "Hosting / deploy"}

# dimension -> [(value, [keywords])]; first keyword hit wins. CONSERVATIVE — only skip a dimension the goal
# clearly already states. Everything else is asked.
_PREFILL = {
    "deliverable": [
        ("CLI tool", ["cli", "command-line", "command line", "terminal tool"]),
        ("library / package", ["library", "package", "pip install", "pypi", "npm package", "sdk"]),
        ("web app", ["web app", "website", "web page", "frontend", "single-page", "spa "]),
        ("REST / GraphQL API", [" api ", "rest api", "restful", "graphql", "endpoint", "microservice"]),
        ("notebook / report", ["notebook", "jupyter", "spreadsheet", "excel", ".csv", "dashboard", " report "]),
        ("data pipeline", ["pipeline", "etl", "ingestion", "batch job"]),
    ],
    "hosting": [
        ("Docker", ["docker", "container"]),
        ("a PaaS (Vercel / Fly / Render)", ["vercel", "fly.io", "render.com", "heroku", "railway"]),
        ("a cloud (AWS / GCP / Azure)", ["aws", "gcp", "google cloud", "azure", "lambda", " s3 "]),
        ("npm / PyPI", ["pypi", "publish to npm", "npm registry"]),
        ("local only", ["local only", "runs locally", "offline"]),
    ],
    "scope": [
        ("quick script", ["quick script", "throwaway", "one-off", "just a script"]),
        ("production-ready", ["production", "production-ready", "prod-ready"]),
        ("an MVP", ["mvp", "minimum viable"]),
    ],
    "purpose": [
        ("learning exercise", ["learning", "practice", "exercise", "tutorial", "to learn"]),
        ("a SaaS / product", ["saas", "startup", "a product", "commercial"]),
        ("open-source library", ["open source", "open-source", "oss "]),
        ("client deliverable", ["client", "for a customer", "consulting"]),
        ("personal / hobby", ["hobby", "personal project", "for fun"]),
    ],
    "users": [
        ("just me", ["just me", "myself", "for my own", "personal use"]),
        ("the public", ["the public", "public users", "general public", "for anyone"]),
        ("my team", ["my team", "our team", "internal team"]),
        ("other developers / an API consumer", ["other developers", "api consumer", "developers who"]),
    ],
}

_STACK_TOKENS = ["python", "java", "javascript", "typescript", "node", "rust", "golang", "c++", "c#",
                 "ruby", "php", "swift", "kotlin", "react", "vue", "svelte", "django", "flask", "fastapi",
                 "express", "next.js", "nextjs", "postgres", "mysql", "sqlite", "mongodb", "redis"]


def prefill(goal):
    """{dim_key: detected_value} for ONLY the dimensions the goal clearly already states (so they aren't
    re-asked). Conservative — no match => absent => ask it. Never guesses."""
    g = " " + " ".join((goal or "").lower().split()) + " "
    out = {}
    for dim, table in _PREFILL.items():
        for value, kws in table:
            if any(k in g for k in kws):
                out[dim] = value
                break
    hits = [t for t in _STACK_TOKENS if t in g]
    if hits:
        out["stack"] = ", ".join(sorted(set(hits)))
    return out


def render_md(answers):
    """The CLARIFIED_GOAL.md 'Framing' section. A dimension with no answer is written 'unspecified' — honest:
    we asked (or skipped) and it wasn't pinned, rather than a silent guess."""
    a = answers or {}
    lines = ["## Framing (project context — #48)"]
    for dim in FRAMING:
        k = dim["key"]
        v = a.get(k)
        lines.append("- **%s:** %s" % (_LABELS[k], v if (v is not None and str(v).strip()) else "unspecified"))
    return "\n".join(lines)


def framing_summary(answers):
    """A one-line brief of the pinned dimensions, for the analyst prompt / Advocate charter (only the ones that
    were actually answered)."""
    a = answers or {}
    parts = ["%s=%s" % (_LABELS[dim["key"]].lower(), a[dim["key"]]) for dim in FRAMING
             if a.get(dim["key"]) is not None and str(a.get(dim["key"])).strip()]
    return "; ".join(parts)
