# lathe-generated module — do not edit by hand


def compute_acceptance_verdict(metrics: dict, thresholds: dict) -> dict:
    failing_gates = [
        key for key in thresholds
        if metrics.get(key, 0) < thresholds[key]
    ]
    return {
        "passed": len(failing_gates) == 0,
        "failing_gates": failing_gates,
    }

def extract_test_count_from_plan(plan: dict) -> int:
    total = 0
    functions = plan.get("FUNCTIONS", [])
    for func in functions:
        tests = func.get("tests", [])
        total += len(tests)
    return total

def format_acceptance_report(verdict: dict) -> str:
    if verdict["passed"]:
        return "BUILD ACCEPTED"
    if verdict["failing_gates"]:
        return "BUILD REJECTED: " + ", ".join(verdict["failing_gates"])
    return "BUILD REJECTED"

def validate_function_spec(spec: dict) -> list:
    errors = []
    
    name = spec.get("name")
    if name is None or name == "":
        errors.append("missing name")
    
    prompt = spec.get("prompt")
    if prompt is None or len(prompt) < 30:
        errors.append("prompt too short")
    
    tests = spec.get("tests")
    if tests is None or len(tests) == 0:
        errors.append("no tests")
    
    return errors

