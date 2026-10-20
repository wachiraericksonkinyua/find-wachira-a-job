from collections import defaultdict, deque
from threading import Lock
import time


class SlidingWindowLimiter:
    """Allow N hits per client inside a rolling time window.

    Each client gets a deque of timestamps. Before checking, timestamps older
    than the window are dropped from the left. If fewer than N remain, the hit
    is allowed and its timestamp is appended. If N remain, the hit is refused.
    """

    def __init__(self, max_requests: int, window_seconds: int):#the code in () means the parameters that are passed to the constructor when creating an instance of the SlidingWindowLimiter class. In this case, max_requests is an integer representing the maximum number of requests allowed within the specified time window, and window_seconds is an integer representing the duration of the time window in seconds.
        self.max_requests = max_requests#self means that the variable belongs to the instance of the class. It allows each instance of SlidingWindowLimiter to have its own max_requests value, which can be different from other instances of the same class.
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        #dict[str, deque[float]] is a type hint indicating that self._hits is a dictionary where the keys are strings (representing client identifiers) and the values are deques (double-ended queues) containing floating-point numbers (representing timestamps of hits).
        #= defaultdict(deque) initializes self._hits as a defaultdict, which is a subclass of the built-in dict class. It automatically creates a new deque for any key that doesn't exist in the dictionary when accessed. This means that if a client identifier is not present in self._hits, it will automatically create an empty deque for that client when accessed.
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._hits[key]

            # Slide the window: forget hits that fell out of range.
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            self._maybe_sweep(cutoff)
            return True

    def _maybe_sweep(self, cutoff: float) -> None:
        """Drop fully expired clients so the dict cannot grow forever."""
        if len(self._hits) < 1000:
            return
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]


# One shared limiter per process: 5 interactions per minute per IP.
interact_limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
