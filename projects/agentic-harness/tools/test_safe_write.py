"""A1 tests — executable spec for safe writes. Run: python tools/test_safe_write.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from safe_write import safe_write, is_write_denied, verify_python


def main():
    d = tempfile.mkdtemp(prefix="safe_write_")
    app = os.path.join(d, "app.py")

    # 1. valid python writes cleanly
    ok, err = safe_write(app, "from fastapi import FastAPI\napp = FastAPI()\n")
    assert ok and err == "", f"valid write rejected: {err}"
    assert open(app).read().count("import FastAPI") == 1

    # 2. THE corruption is REFUSED and the original file is untouched
    ok, err = safe_write(app, "rom fastapi import FastAPI\n" * 268)
    assert ok is False and "broken Python" in err, f"corruption was not refused: {ok}/{err}"
    assert open(app).read() == "from fastapi import FastAPI\napp = FastAPI()\n", "original file was clobbered"

    # 3. credential / system / .git paths are denied
    for bad in [os.path.join(d, ".env"), os.path.join(d, "id_rsa"),
                os.path.join(d, ".git", "config"), r"C:\Windows\system32\drivers\etc\hosts"]:
        assert is_write_denied(bad), f"should deny {bad}"
        ok, err = safe_write(bad, "x")
        assert ok is False and "denied" in err

    # 4. atomic full-replace (no partial / leftover temp files)
    big = os.path.join(d, "data.txt")
    safe_write(big, "A" * 10000)
    safe_write(big, "B" * 5)
    assert open(big).read() == "BBBBB", "not a clean full replace"
    assert not any(n.startswith(".tmp_") for n in os.listdir(d)), "temp file leaked"

    # 5. non-.py content is written without the syntax gate (even 'garbage')
    txt = os.path.join(d, "notes.txt")
    ok, err = safe_write(txt, "rom fastapi this is not python")
    assert ok and open(txt).read().startswith("rom"), "non-py write should pass"

    # 6. verify_syntax=False bypasses the check (escape hatch)
    ok, err = safe_write(app, "def broken(:\n", verify_syntax=False)
    assert ok, "verify_syntax=False should allow it"

    # 7. verify_python helper: good vs bad
    assert verify_python("x = 1\n") is None
    assert "SyntaxError" in verify_python("def f(:\n")

    print("A1 safe_write: ALL 7 ASSERTIONS PASS — broken Python can't reach disk; creds protected; writes atomic.")


if __name__ == "__main__":
    main()
