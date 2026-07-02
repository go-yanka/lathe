# lathe-generated module — do not edit by hand


def bucket_of(name, capability, role):
    try:
        parts = []
        for v in (name, capability, role):
            parts.append(v if isinstance(v, str) else '')
        haystack = ' '.join(parts).lower()
        buckets = [
            ('review', ['review', 'adversarial', 'correctness', 'guardian', 'auditor', 'judge', 'standards']),
            ('security', ['security', 'vulnerab', 'exploit', 'threat', 'malware', 'authenticat', 'authoriz', 'pentest', 'owasp', 'injection']),
            ('testing-qa', ['test', 'qa', 'debug', 'playwright', 'tdd', 'coverage', 'mutation']),
            ('data-ai', ['data', 'ml', 'ai-', 'ai engineer', 'mlops', 'quant', 'vector', 'prompt', 'eval', 'model', 'database', 'sql', 'analytics']),
            ('devops-cloud', ['devops', 'deploy', 'kubernetes', 'terraform', 'cloud', 'network', 'incident', 'observ', 'infra', 'sre', 'docker', 'pipeline']),
            ('frontend-mobile', ['frontend', 'ui-', 'ux-', 'react', 'ios', 'android', 'flutter', 'mobile', 'accessib', 'unity']),
            ('language', ['-pro', 'python', 'rust', 'golang', 'java', 'cpp', 'c-pro', 'ruby', 'php', 'scala', 'bash', 'typescript', 'javascript', 'elixir', 'haskell', 'julia', 'kotlin', 'swift', 'dotnet', 'csharp']),
            ('architecture', ['architect', 'design', 'monorepo', 'event-sourcing', 'c4', 'graphql', 'api', 'microservice', 'system']),
            ('docs-content', ['doc', 'tutorial', 'seo', 'content', 'market', 'writer', 'reference', 'blog']),
        ]
        for bucket, keywords in buckets:
            if any(k in haystack for k in keywords):
                return bucket
        return 'specialized'
    except Exception:
        return 'specialized'

def ensure_ce_floor(picked, ce_names, default_ce):
    try:
        picked_list = list(picked) if picked is not None else []
        ce_set = set(ce_names) if ce_names is not None else set()
        if not ce_set:
            return picked_list
        if any(name in ce_set for name in picked_list):
            return picked_list
        if isinstance(default_ce, str) and default_ce and default_ce in ce_set:
            chosen = default_ce
        else:
            chosen = next(iter(list(ce_names)), None)
        if chosen is None:
            return picked_list
        return [chosen] + picked_list
    except Exception:
        try:
            return list(picked) if picked is not None else []
        except Exception:
            return []

