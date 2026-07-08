# lathe-generated module — do not edit by hand


def gate_infra_failure(output):
    if not isinstance(output, str):
        return False
    lowered = output.lower()
    signatures = (
        "executable doesn't exist",
        "browsertype.launch",
        "playwright was just installed",
        "playwright install",
        "no module named",
        "failed to launch",
        "browser closed unexpectedly",
        "target page, context or browser has been closed",
        "econnrefused",
    )
    return any(sig in lowered for sig in signatures)

