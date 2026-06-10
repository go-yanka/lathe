# A minimal Lathe plan: build a tiny `calc` module, each function spec'd + test-gated, then pinned.
# Run:  python ../../engine.py plan_add.py gemma4:12b 3   (from this dir, or pass the full path)
#
# Re-run it and the functions are reused from .pins.json (reproducible) instead of re-generated.
# Change a prompt or a test and only that function regenerates. Code is a build output — don't edit calc.py.

MODULE_NAME = "calc"            # -> writes calc.py in this directory
HEADER = ""                    # no imports needed

FUNCTIONS = [
    {
        "name": "add",
        "prompt": "Write a Python function `add(a, b)` that returns the sum of two numbers.",
        "tests": [
            "assert add(2, 3) == 5",
            "assert add(-1, 1) == 0",
            "assert add(0, 0) == 0",
        ],
    },
    {
        "name": "is_even",
        "prompt": "Write a Python function `is_even(n)` that returns True if the integer n is even, else False.",
        "tests": [
            "assert is_even(4) is True",
            "assert is_even(7) is False",
            "assert is_even(0) is True",
        ],
    },
    {
        "name": "fizzbuzz",
        "prompt": ("Write a Python function `fizzbuzz(n)`: return 'FizzBuzz' if n is divisible by both 3 "
                   "and 5, 'Fizz' if divisible by 3, 'Buzz' if divisible by 5, otherwise the number as a string."),
        "tests": [
            "assert fizzbuzz(15) == 'FizzBuzz'",
            "assert fizzbuzz(9) == 'Fizz'",
            "assert fizzbuzz(10) == 'Buzz'",
            "assert fizzbuzz(7) == '7'",
        ],
    },
]

# GLUE is hand-authored wiring appended verbatim (not generated). Here, a tiny convenience function.
GLUE = """
def summarize(n):
    return f"{n}: even={is_even(n)} fizzbuzz={fizzbuzz(n)} (n+1={add(n, 1)})"
"""

# INTEGRATION imports the built module and asserts the whole thing works together (exit 0 = pass).
INTEGRATION = """
import calc
assert calc.add(10, 5) == 15
assert calc.is_even(10) and not calc.is_even(11)
assert calc.fizzbuzz(30) == 'FizzBuzz'
assert calc.summarize(15) == '15: even=False fizzbuzz=FizzBuzz (n+1=16)'
print("CALC OK — add + is_even + fizzbuzz + glue, all gated")
"""
