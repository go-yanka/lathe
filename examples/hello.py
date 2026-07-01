# Lathe demo plan — `python lathe.py build examples/hello.py`
# Ships with its pin, so it rebuilds deterministically OFFLINE (no model endpoint needed) — proof of the
# pinning / reproducibility story. Delete examples/.pins.json to force a real model build.
OUT_DIR = "examples"
MODULE_NAME = "hello_lathe"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "greet",
        "prompt": ("Write greet(name) that returns 'Hello, ' + name + '!'. If name is falsy, return "
                   "'Hello, world!'. Output ONLY the function code."),
        "tests": [
            "assert greet('Ada') == 'Hello, Ada!'",
            "assert greet('') == 'Hello, world!'",
            "assert greet(None) == 'Hello, world!'",
            "assert greet('x') == 'Hello, x!'",
        ],
    }
]
