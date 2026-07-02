# H_persona_market — the persona library's organization + governance (owner directive): every agent gets a
# BUCKET (when-to-invoke), and every decider call is guaranteed at least one Compound-Engineering reviewer
# (CE personas are the strongest; they hold a floor). Pure pieces here; the spine wires them into selection.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_market"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "bucket_of",
     "prompt": ("Write bucket_of(name, capability, role) -> str. Classify an expert persona into ONE domain "
                "bucket so the decider knows when to reach for it. Build a lowercase haystack from name + ' ' + "
                "capability + ' ' + role (each coerced to '' if None/non-str). Return the FIRST bucket whose any "
                "keyword appears as a substring, checked in THIS order: "
                "'review' if any of [review, adversarial, correctness, guardian, auditor, judge, standards]; "
                "'security' if any of [security, vulnerab, exploit, threat, malware, authenticat, authoriz, pentest, owasp, injection]; "
                "'testing-qa' if any of [test, qa, debug, playwright, tdd, coverage, mutation]; "
                "'data-ai' if any of [data, ml, ai-, ai engineer, mlops, quant, vector, prompt, eval, model, "
                "database, sql, analytics]; "
                "'devops-cloud' if any of [devops, deploy, kubernetes, terraform, cloud, network, incident, "
                "observ, infra, sre, docker, pipeline]; "
                "'frontend-mobile' if any of [frontend, ui-, ux-, react, ios, android, flutter, mobile, "
                "accessib, unity]; "
                "'language' if any of [-pro, python, rust, golang, java, cpp, c-pro, ruby, php, scala, bash, "
                "typescript, javascript, elixir, haskell, julia, kotlin, swift, dotnet, csharp]; "
                "'architecture' if any of [architect, design, monorepo, event-sourcing, c4, graphql, api, "
                "microservice, system]; "
                "'docs-content' if any of [doc, tutorial, seo, content, market, writer, reference, blog]; "
                "otherwise 'specialized'. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert bucket_of('correctness-reviewer', 'logic errors', 'reviewer') == 'review'",
        "assert bucket_of('security-auditor', 'owasp vulnerabilities', 'reviewer') == 'review'",
        "assert bucket_of('threat-modeling-expert', 'stride attack surface', 'analyst') == 'security'",
        "assert bucket_of('rust-pro', 'systems memory safety', 'implementer') == 'language'",
        "assert bucket_of('kubernetes-architect', 'k8s helm autoscaling deploy', 'analyst') == 'devops-cloud'",
        "assert bucket_of('ml-engineer', 'model training pipelines', 'analyst') == 'data-ai'",
        "assert bucket_of('accessibility-expert', 'aria wcag screen reader', 'implementer') == 'frontend-mobile'",
        "assert bucket_of('graphql-architect', 'schema federation resolvers', 'analyst') == 'architecture'",
        "assert bucket_of('tutorial-engineer', 'docs how-to guides', 'implementer') == 'docs-content'",
        "assert bucket_of('blockchain-developer', 'solidity smart contracts', 'implementer') == 'specialized'",
        "assert bucket_of(None, None, None) == 'specialized'",
        "assert bucket_of('test-automator', 'coverage e2e', 'implementer') == 'testing-qa'",
     ]},
    {"name": "ensure_ce_floor",
     "prompt": ("Write ensure_ce_floor(picked, ce_names, default_ce) -> list. Governance rule: the Compound-"
                "Engineering reviewers are the strongest personas, so every decider selection must include at "
                "least one. picked is the decider's chosen name list (None -> []). ce_names is the set/list of "
                "CE persona names (None -> []). If ANY name in picked is in ce_names, return picked unchanged "
                "(as a list). Otherwise return a NEW list with default_ce PREPENDED to picked — but only if "
                "default_ce is a non-empty string AND is in ce_names; if default_ce is not a valid CE name, "
                "fall back to the FIRST name in ce_names; if ce_names is empty, return picked unchanged. Never "
                "duplicate (if default_ce already in picked, unchanged). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert ensure_ce_floor(['rust-pro'], ['correctness-reviewer', 'adversarial-reviewer'], 'correctness-reviewer') == ['correctness-reviewer', 'rust-pro']",
        "assert ensure_ce_floor(['adversarial-reviewer', 'rust-pro'], ['correctness-reviewer', 'adversarial-reviewer'], 'correctness-reviewer') == ['adversarial-reviewer', 'rust-pro']",
        "assert ensure_ce_floor(['rust-pro'], ['correctness-reviewer', 'adversarial-reviewer'], 'nonsense') == ['correctness-reviewer', 'rust-pro']",
        "assert ensure_ce_floor(['rust-pro'], [], 'correctness-reviewer') == ['rust-pro']",
        "assert ensure_ce_floor(None, ['correctness-reviewer'], 'correctness-reviewer') == ['correctness-reviewer']",
        "assert ensure_ce_floor(['correctness-reviewer'], ['correctness-reviewer'], 'correctness-reviewer') == ['correctness-reviewer']",
        "assert ensure_ce_floor([], ['a-reviewer', 'b-reviewer'], '') == ['a-reviewer']",
     ]},
]
