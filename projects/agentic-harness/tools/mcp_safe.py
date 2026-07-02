# lathe-generated module — do not edit by hand


def reject_flags(s):
    """
    Analyze a string for CLI-style flags.
    
    Args:
        s: Input to analyze
        
    Returns:
        [ok, tokens] where:
        - ok is False if any token starts with '-' (potential argument injection)
        - tokens is the list of whitespace-split tokens
        - If s is not a string, returns [False, []] to fail closed
    """
    # Import is not needed as we're not using any external libraries
    if not isinstance(s, str):
        return [False, []]
    
    tokens = s.split()
    has_flags = any(token.startswith('-') for token in tokens)
    
    return [not has_flags, tokens]

def is_within_root(root, path):
    """
    Check if `path` is within `root`, considering symlinks, case sensitivity,
    and edge cases like different drives or None/empty paths.

    :param root: The root path.
    :param path: The path to check.
    :return: True if `path` is within `root`, False otherwise.
    """
    import os

    # Return False for None or empty paths
    if path is None or path == "":
        return False

    # If path is not absolute, join it with root first
    if not os.path.isabs(path):
        path = os.path.join(root, path)

    try:
        # Resolve both root and path to their real, normalized forms
        real_root = os.path.normcase(os.path.realpath(root))
        real_target = os.path.normcase(os.path.realpath(path))

        # Find the common path between the resolved root and target
        common = os.path.commonpath([real_root, real_target])

        # Check if the common path is the root
        return common == real_root
    except (ValueError, TypeError):
        # Handle errors like paths on different drives or invalid path types
        return False

