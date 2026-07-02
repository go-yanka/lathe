# lathe-generated module — do not edit by hand


def score_match(need, capability):
    import re
    def word_set(s):
        if s is None:
            return set()
        if not isinstance(s, str):
            return set()
        if not s.strip():
            return set()
        lower = s.lower()
        parts = re.split(r'[^a-z0-9]+', lower)
        return set(p for p in parts if p)
    s1 = word_set(need)
    s2 = word_set(capability)
    return len(s1 & s2)

def license_ok(lic):
    if lic is None:
        return False
    if not isinstance(lic, str):
        return False
    cleaned = lic.strip().lower()
    prefixes = ('mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0')
    return any(cleaned.startswith(p) for p in prefixes)

def select_agents_for_goal(goal, entries, k):
    """
    Select k agents best suited for a given goal based on word overlap in capabilities.
    
    Args:
        goal (str): The goal description
        entries (list): List of [name, capability] pairs
        k (int): Number of agents to return
        
    Returns:
        list: Names of the top k agents sorted by relevance
    """
    import re
    
    # Handle invalid inputs
    if not goal or not entries or k <= 0:
        return []
    
    # Convert goal to lowercase and split into words
    goal_words = set(re.split(r'[^a-z0-9]+', goal.lower()))
    goal_words.discard('')  # Remove empty strings if any
    
    scored_entries = []
    
    for idx, entry in enumerate(entries):
        if len(entry) < 2:
            continue
            
        name, capability = entry[0], entry[1]
        
        # Convert capability to lowercase and split into words
        cap_words = set(re.split(r'[^a-z0-9]+', capability.lower()))
        cap_words.discard('')
        
        # Calculate score as number of shared distinct words
        shared_words = goal_words.intersection(cap_words)
        score = len(shared_words)
        
        if score > 0:
            scored_entries.append((idx, name, score))
    
    # Sort by score descending, then by original order (index) ascending
    scored_entries.sort(key=lambda x: (-x[2], x[0]))
    
    # Extract names of top k agents
    result = [name for idx, name, score in scored_entries[:k]]
    
    return result

def pick_best(need, entries):
    if not entries:
        return ''
    try:
        need_words = set(need.lower().split()) if need else set()
        best_name = ''
        best_score = 0
        for entry in entries:
            try:
                name = entry[0]
                capability = entry[1]
                entry_words = set(capability.lower().split())
                if not need_words or not entry_words:
                    score = 0
                else:
                    score = len(need_words & entry_words)
                if score > best_score:
                    best_score = score
                    best_name = name
            except Exception:
                continue
        return best_name if best_score > 0 else ''
    except Exception:
        return ''

