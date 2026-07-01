# lathe-generated module — do not edit by hand


def should_retry(attempt, max_attempts, exc_name, retryable=None):
    """
    Decide whether a failed task attempt should be retried.
    
    Args:
        attempt: The attempt number that just FAILED (1-based).
        max_attempts: The total allowed attempts.
        exc_name: The class name of the exception that was raised.
        retryable: Optional iterable of retryable exception class names.
                   If None, uses default: ('TimeoutError', 'ConnectionError', 
                   'RuntimeError', 'OSError').
    
    Returns:
        True if the attempt should be retried, False otherwise.
    """
    # Define default retryable exceptions inside the function
    if retryable is None:
        retryable = ('TimeoutError', 'ConnectionError', 'RuntimeError', 'OSError')
    
    # Check if attempt is less than max_attempts
    if attempt >= max_attempts:
        return False
    
    # Check if exc_name is in the retryable set
    if exc_name not in retryable:
        return False
    
    return True

def backoff_delay(attempt, base=0.5, cap=30.0) -> float:
    if attempt < 1:
        return 0.0
    delay = base * (2 ** (attempt - 1))
    return min(max(delay, 0.0), cap)

