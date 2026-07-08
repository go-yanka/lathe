# lathe-generated module — do not edit by hand


def slugify_goal(goal, max_len=40):
    if not isinstance(goal, str) or not goal.strip():
        return 'goal'
    if max_len is None or max_len < 8:
        max_len = 8
    slug = goal.lower()
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = slug[:max_len].rstrip('-')
    return slug if slug else 'goal'

def pick_focus(goal):
    import re
    if goal is None or not isinstance(goal, str):
        return 'helper'
    webapp_words = r'\b(?:html|webpage|web|website|page|ui|frontend|browser|canvas|dashboard|game|app)\b'
    if re.search(webapp_words, goal, re.IGNORECASE):
        return 'webapp'
    return 'helper'

def workspace_rel(slug, stamp):
    def sanitize(value, fallback):
        if not value:
            return fallback
        cleaned = value.replace('/', '').replace('\\', '').replace('.', '')
        return cleaned if cleaned else fallback
    return 'goals/' + sanitize(slug, 'goal') + '_' + sanitize(stamp, 'run')

