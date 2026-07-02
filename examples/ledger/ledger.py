# lathe-generated module — do not edit by hand


def summarize(lines):
    try:
        if not lines:
            return {'total': 0.0, 'by_category': {}, 'top': None}
        
        from ledger_core import parse_entry
        from ledger_stats import total, by_category, top_category
        
        entries = []
        for line in lines:
            if line is None or line.strip() == '':
                continue
            parsed = parse_entry(line)
            if parsed is not None:
                entries.append(parsed)
                
        if not entries:
            return {'total': 0.0, 'by_category': {}, 'top': None}
            
        return {
            'total': total(entries),
            'by_category': by_category(entries),
            'top': top_category(entries)
        }
    except Exception:
        return {'total': 0.0, 'by_category': {}, 'top': None}

