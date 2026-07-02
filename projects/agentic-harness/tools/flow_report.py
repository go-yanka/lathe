# lathe-generated module — do not edit by hand


def classify_step(kind, rc, output) -> str:
    failure_signals = ['not exist', 'could be read', 'traceback', 'fail ::', 'error:']
    try:
        if kind == 'you':
            return 'todo'
        out_str = output if output is not None else ''
        if isinstance(rc, int) and rc != 0:
            return 'blocked'
        out_lower = out_str.lower()
        for signal in failure_signals:
            if signal in out_lower:
                return 'blocked'
        return 'pass'
    except Exception:
        return 'blocked'

def workflow_verdict(statuses: list) -> str:
    PASS = 'PASS'
    BLOCKED = 'BLOCKED'
    
    if not statuses:
        return PASS
    
    for status in statuses:
        if status == 'blocked':
            return BLOCKED
    
    return PASS

def render_report(name: str, rows: list) -> str:
    """
    Render a workflow report string.

    Parameters
    ----------
    name : str
        The workflow name.
    rows : list[tuple[str, str]]
        List of (label, status) tuples. Each status must be one of
        'pass', 'blocked', or 'todo'.

    Returns
    -------
    str
        Multi-line report string.
    """
    # Import datetime to get a timestamp for the report.
    from datetime import datetime

    # Define constants for status strings.
    STATUS_PASS = "PASS"
    STATUS_BLOCKED = "BLOCKED"
    STATUS_TODO = "TODO"

    # Default rows to an empty list if None.
    if rows is None:
        rows = []

    # Validate and normalize status.
    def normalize_status(status: str) -> str:
        """
        Normalize the status string.

        Parameters
        ----------
        status : str
            The status string.

        Returns
        -------
        str
            The normalized status string.
        """
        if status is None:
            return STATUS_TODO
        status = status.strip().lower()
        if status not in ("pass", "blocked", "todo"):
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Must be one of: pass, blocked, todo."
            )
        if status == "pass":
            return STATUS_PASS
        elif status == "blocked":
            return STATUS_BLOCKED
        elif status == "todo":
            return STATUS_TODO

    # Build the report lines.
    report_lines = [f"workflow report: {name}"]

    # Track if any row is blocked.
    has_blocked = False

    for label, status in rows:
        # Normalize the status.
        normalized_status = normalize_status(status)

        # Add the row line.
        report_lines.append(f"  [{normalized_status}] {label}")

        # Check for blocked status.
        if normalized_status == STATUS_BLOCKED:
            has_blocked = True

    # Determine the verdict.
    if has_blocked:
        verdict = STATUS_BLOCKED
    else:
        verdict = STATUS_PASS

    # Add the verdict line.
    report_lines.append(f"verdict: {verdict}")

    # Join the lines with newlines.
    report = "\n".join(report_lines)

    return report

