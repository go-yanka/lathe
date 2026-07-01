# lathe-generated module — do not edit by hand


def spec_static_gaps(tests_text):
    import re

    if not isinstance(tests_text, str):
        tests_text = ''

    gaps = []

    # (1) if 'None' does not appear in the text
    if 'None' not in tests_text:
        gaps.append('no None/null case')

    # (2) if none of these empty-value tokens appear as substrings
    empty_tokens = ["''", '""', '[]', '{}']
    has_any_empty = any(token in tests_text for token in empty_tokens)
    if not has_any_empty:
        gaps.append('no empty case')

    # (3) if there is no standalone zero (regex \b0\b) in the text
    if not re.search(r'\b0\b', tests_text):
        gaps.append('no zero case')

    # (4) if the text contains fewer than 3 occurrences of the word 'assert'
    if len(re.findall(r'assert', tests_text)) < 3:
        gaps.append('too few assertions (<3)')

    return sorted(gaps)

