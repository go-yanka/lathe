# lathe-generated module — do not edit by hand


def analyst_response_ok(txt, markers):
    try:
        if not isinstance(txt, str) or len(txt.strip()) < 40:
            return [False, 'too short to be a review']
        if isinstance(markers, list) and markers:
            valid = [m for m in markers if isinstance(m, str) and m.strip()]
            if valid:
                low = txt.lower()
                if not any(m.lower() in low for m in valid):
                    return [False, 'response mentions neither a severity nor a reviewed file (wrong-200 guard)']
        return [True, 'ok']
    except Exception:
        return [False, 'too short to be a review']

