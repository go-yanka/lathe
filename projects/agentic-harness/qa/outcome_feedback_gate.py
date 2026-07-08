"""outcome_feedback_gate.py — MASTER_PLAN E4 proof: review outcomes update persona ratings correctly + safely.

Drives tools/outcome_feedback.py with INJECTED (in-memory) ratings persistence and asserts: an 'engaged'
outcome raises a lens's rating toward the outcome score (EWMA-blended, not overwritten), an 'inoperative'
outcome is SKIPPED (no signal), fetched-by-path lenses (@...) are skipped, and nothing raises. So the
learning loop can't silently regress or corrupt the store.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import outcome_feedback as of   # noqa: E402


def main():
    problems = []

    # score mapping
    if of.score_verdict("inoperative") is not None or of.score_verdict("engaged") is None:
        problems.append("score_verdict mapping wrong")
    if of.score_verdict("material") <= of.score_verdict("clean"):
        problems.append("material should score higher than clean")

    # in-memory store
    store = {"correctness": {"rating": 0.50}}

    def load():
        return store

    def save(name, score, need):
        store[name] = {"rating": round(float(score), 3), "need": need}
        return store[name]

    # engaged outcome nudges UP toward 0.70 but stays blended (not a jump to 0.70), and persists.
    upd = of.record_review_outcomes({"correctness": "engaged"}, load, save, prior_weight=5)
    r = store["correctness"]["rating"]
    if not (0.50 < r < 0.70):
        problems.append("engaged did not EWMA-nudge up between prior and score: %r" % r)
    if "correctness" not in upd:
        problems.append("record did not return the updated lens")

    # inoperative -> no update (skipped), fetched-by-path lens -> skipped.
    before = dict(store)
    upd2 = of.record_review_outcomes({"correctness": "inoperative", "@/tmp/x.md": "engaged"}, load, save)
    if upd2:
        problems.append("inoperative + @-path should produce NO updates: %r" % upd2)
    if store != before:
        problems.append("inoperative/@-path must not mutate the store")

    # a new lens with no prior starts from 0.5 and updates.
    of.record_review_outcomes({"security": "material"}, load, save)
    if "security" not in store or not (0.5 < store["security"]["rating"] <= 1.0):
        problems.append("new lens not initialized+updated from prior 0.5: %r" % store.get("security"))

    # never raises on a broken saver.
    def _boom(*a):
        raise RuntimeError("disk full")
    try:
        of.record_review_outcomes({"correctness": "engaged"}, load, _boom)
    except Exception as e:
        problems.append("a raising save_rating propagated: %s" % e)

    if problems:
        print("outcome-feedback gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("outcome-feedback gate: PASS — review outcomes EWMA-blend into ratings (engaged up, inoperative "
          "skipped, @-path skipped, new lens from prior, never raises)")
    sys.exit(0)


if __name__ == "__main__":
    main()
