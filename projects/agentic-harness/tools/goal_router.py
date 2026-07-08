# lathe-generated module — do not edit by hand


def slugify_goal(goal, max_len=40):
    import re
    if goal is None or not isinstance(goal, str) or not goal.strip():
        return 'goal'
    if max_len is None or max_len < 8:
        max_len = 8
    slug = re.sub(r'[^a-z0-9]+', '-', goal.lower())
    slug = slug.strip('-')
    slug = slug[:max_len].rstrip('-')
    return slug if slug else 'goal'

def pick_focus(goal):
    import re
    if not isinstance(goal, str):
        return 'helper'
    webapp_words = ('html', 'webpage', 'web', 'website', 'page', 'ui',
                    'frontend', 'browser', 'canvas', 'dashboard', 'game', 'app')
    pattern = r'\b(?:' + '|'.join(webapp_words) + r')\b'
    if re.search(pattern, goal, re.IGNORECASE):
        return 'webapp'
    return 'helper'

def short_goal(goal, max_words=4, max_len=24):
    import re
    if goal is None or not isinstance(goal, str) or not goal.strip():
        return 'goal'
    stopwords = {
        'a', 'an', 'the', 'with', 'using', 'for', 'of', 'in', 'on', 'to',
        'and', 'or', 'that', 'this', 'which', 'single', 'file', 'page',
        'html', 'web', 'website', 'webpage', 'app', 'application', 'simple',
        'complete', 'basic', 'small', 'tiny', 'create', 'build', 'make',
        'implement', 'write', 'shows', 'shown', 'show', 'display',
        'displayed', 'style', 'styled', 'retro', 'classic',
    }
    words = [
        w for w in re.split(r'[^a-z0-9]+', goal.lower())
        if w and len(w) >= 2 and w not in stopwords
    ]
    slug = '-'.join(words[:max_words])
    if len(slug) > max_len:
        cut = slug[:max_len]
        if slug[max_len] != '-':
            i = cut.rfind('-')
            if i != -1:
                cut = cut[:i]
        slug = cut.rstrip('-')
    if not slug:
        return 'goal'
    return slug

def model_abbrev(model):
    import re
    if model is None or not isinstance(model, str) or not model.strip():
        return 'model'
    s = model.lower()
    for name in ('fable', 'claude', 'sonnet', 'opus', 'haiku', 'gpt', 'gemini'):
        if name in s:
            return name
    m = re.search(r'(\d+(?:\.\d+)?)\s*[bB]\b', model)
    if m:
        return m.group(1).lower() + 'b'
    if ':' in s:
        s = s.rsplit(':', 1)[1]
    s = re.sub(r'[^a-z0-9]', '', s)[:8]
    return s if s else 'model'

def workspace_rel(slug, stamp):
    def sanitize(value, fallback):
        if not value:
            return fallback
        cleaned = value.replace('/', '').replace('\\', '').replace('.', '')
        if not cleaned:
            return fallback
        return cleaned
    return 'goals/' + sanitize(slug, 'goal') + '_' + sanitize(stamp, 'run')

