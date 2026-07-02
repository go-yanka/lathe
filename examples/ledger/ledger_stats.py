# lathe-generated module — do not edit by hand


def total(entries):
    try:
        from functools import reduce
        if not entries:
            return 0.0
        return round(reduce(lambda a, b: a + b, [e.get('amount', 0.0) for e in entries if isinstance(e, dict) and 'amount' in e]), 2)
    except Exception:
        return 0.0

def by_category(entries):
    """
    Sum 'amount' by 'category' for each entry in the list.

    - If `entries` is None or empty, returns {}.
    - Returns a dict mapping category -> total amount (rounded to 2 decimals).
    - Never raises.
    """
    try:
        if not entries:
            return {}

        totals = {}
        for entry in entries:
            try:
                cat = entry.get('category')
                amt = entry.get('amount')
                if cat is None or amt is None:
                    continue
                if not isinstance(amt, (int, float)):
                    continue
                totals[cat] = totals.get(cat, 0) + amt
            except (TypeError, AttributeError):
                continue

        return {k: round(v, 2) for k, v in totals.items()}
    except Exception:
        return {}

def top_category(entries):
    from collections import defaultdict
    
    try:
        if not entries:
            return None
        
        sums = defaultdict(float)
        for entry in entries:
            category = entry.get('category', '')
            amount = entry.get('amount', 0)
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                amount = 0
            sums[category] += amount
        
        if not sums:
            return None
        
        max_category = max(sums, key=lambda k: sums[k])
        return max_category
    except Exception:
        return None

