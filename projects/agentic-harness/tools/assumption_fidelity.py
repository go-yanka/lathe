"""assumption_fidelity.py — did the AGREED input survive into the build?

The input line is: goal -> discovery -> assumptions -> the user CONFIRMS choices -> those get injected into the
goal the analyst drafts from. But nothing PROVES each confirmed choice actually reached the drafted spec + the
built artifact; the analyst could quietly drop one, and only the (fallible) Advocate at delivery might notice.

This module is the deterministic proxy for "carried forward": for each confirmed assumption, do its DISTINCTIVE
terms appear in the drafted spec / artifact text? A choice whose terms are largely ABSENT is flagged as
*possibly dropped* — an advisory signal (lexical presence is not proof of honouring, so it warns + feeds the
Advocate rather than hard-blocking, to avoid false-positives on validly-reworded specs).

Pure + injectable so a gate proves the logic deterministically.
"""

import re

_STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "is", "are", "be", "it", "its", "as", "at",
         "by", "for", "with", "not", "no", "than", "then", "so", "that", "this", "each", "any", "will", "would",
         "should", "rather", "instead", "default", "e.g", "eg", "etc", "game", "page", "user", "when", "which",
         "into", "from", "per", "up", "down", "via", "if", "else"}


def _terms(s):
    return {t for t in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split() if len(t) > 2 and t not in _STOP}


def unhonored(confirmed, drafted_text, min_overlap=0.34):
    """Return the confirmed assumptions whose distinctive terms are largely ABSENT from `drafted_text` — the
    choices the spec appears to have dropped. `confirmed` is a list of strings (or {'text':..} dicts).
    Each result: {'assumption', 'overlap'}. An empty result == every agreed choice is reflected.

    The bar is deliberately LOW (a genuinely-dropped choice shares ~0% of its distinctive terms with the spec):
    partial rewordings and honoured-by-omission non-goals ('no touch controls') keep enough overlap to pass, so
    the signal stays trustworthy (few false positives) at the cost of missing a choice that was half-reworded —
    acceptable because this is an advisory feed to the Advocate, not the last line of defence."""
    dtok = _terms(drafted_text)
    out = []
    for a in (confirmed or []):
        txt = a.get("text", "") if isinstance(a, dict) else str(a)
        at = _terms(txt)
        if not at:
            continue
        overlap = len(at & dtok) / len(at)
        if overlap < min_overlap:
            out.append({"assumption": txt, "overlap": round(overlap, 2)})
    return out


def summary(missing, total):
    """One-line advisory for the terminal / the Advocate's context."""
    if not missing:
        return "assumption fidelity: all %d confirmed choice(s) are reflected in the build" % total
    return ("assumption fidelity: %d of %d confirmed choice(s) look DROPPED from the build (verify): %s"
            % (len(missing), total, "; ".join("%r (%.0f%% terms)" % (m["assumption"][:60], m["overlap"] * 100)
                                               for m in missing[:4])))
