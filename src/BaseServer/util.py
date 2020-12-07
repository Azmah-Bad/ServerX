import functools
import time


def log(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_log(*args, **kwargs):
        start_time = time.perf_counter()  # 1
        value = func(*args, **kwargs)
        end_time = time.perf_counter()  # 2
        run_time = end_time - start_time  # 3
        print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value

    return wrapper_log


def isDropped(ACKs: list) -> bool:
    """
    Check if given list contains any duplicates
    :complexity: log(n)
    """
    if len(ACKs) == len(set(ACKs)):
        return False
    return True
