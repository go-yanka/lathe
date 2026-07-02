# lathe-generated module — do not edit by hand


def resolve_out_dir(out_dir: str, plan_path: str) -> str:
    if out_dir:
        return out_dir
    # Use os.path inside the function per instructions
    import os

    abs_path = os.path.abspath(plan_path)
    dir_name = os.path.dirname(abs_path)
    return dir_name

def treat_missing_as_uninitialized(canonical_path):
    if canonical_path is None:
        return False
    
    try:
        suffixes = ('.db', '.sqlite', '.sqlite3')
        lower_path = canonical_path.lower()
        return any(lower_path.endswith(suffix) for suffix in suffixes)
    except Exception:
        return False

def should_auto_commit(env_value):
    """Return True only if env_value is a truthy auto-commit indicator."""
    TRUE_VALUES = {'1', 'true', 'yes', 'on'}
    
    if env_value is None:
        return False
    
    try:
        value_str = str(env_value).strip().lower()
        return value_str in TRUE_VALUES
    except (TypeError, ValueError):
        return False

def integration_label(has_integration, all_passed):
    if not has_integration:
        return 'n/a (no INTEGRATION defined)'
    if not all_passed:
        return 'SKIPPED (not all functions solved)'
    return 'ran'

def model_label(model_name):
    """
    Derive a sanitized model label from a model name.
    
    - If model_name is falsy, return 'local'.
    - Otherwise, convert to str, take the substring before the first ':',
      then strip whitespace and lowercase.
    - Never raise.
    """
    try:
        if not model_name:
            return 'local'
        
        s = str(model_name)
        
        # Find the first colon
        colon_idx = s.find(':')
        if colon_idx != -1:
            s = s[:colon_idx]
        
        return s.strip().lower()
    except Exception:
        return 'local'

def summarize_failure(output):
    """Summarize the failure from the build output.
    Args:
        output: The build output to summarize.
    Returns:
        A string summarizing the failure.
    """
    import io
    import re
    import textwrap
    import sys
    from typing import Iterable

    if output is None:
        return 'build failed'

    lines = str(output).splitlines()

    # Filter blank lines and activity log skipped lines
    relevant_lines = []
    for line in lines:
        if line.strip():
            if 'activity log skipped' not in line.lower():
                relevant_lines.append(line)

    # Search for error lines
    for line in relevant_lines:
        if 'error' in line.lower():
            return line.strip()

    # If no error lines, return the last relevant line
    if relevant_lines:
        return relevant_lines[-1].strip()

    return 'build failed'

