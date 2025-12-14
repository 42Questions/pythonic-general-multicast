from queue import LifoQueue
from typing import Any


def ipv4_to_int(ipv4: str) -> int:
    """Convert IPv4 string to 32-bit integer.

    Args:
        ipv4: IPv4 address string (e.g., "192.168.1.1")

    Returns:
        32-bit integer representation
    """
    parts = ipv4.split(".")
    if len(parts) != 4:
        raise ValueError(f"Invalid IPv4 address: {ipv4}")
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def int_to_ipv4(ip_int: int) -> str:
    """Convert 32-bit integer to IPv4 string.

    Args:
        ip_int: 32-bit integer representation

    Returns:
        IPv4 address string
    """
    return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"


class BoundedLifoQueue(LifoQueue):
    """
    Thread-safe LIFO queue that auto-evicts the oldest item when full.

    Behaves like queue.LifoQueue but when at maxsize, put() will automatically
    remove the oldest (bottom of stack) item instead of blocking or raising Full.

    Thread-safe for concurrent put() and pop()/get() operations across threads.

    Example:
        # Thread 1 (producer)
        q = BoundedLifoQueue(maxsize=3)
        q.put(1)  # [1]
        q.put(2)  # [1, 2]
        q.put(3)  # [1, 2, 3]
        q.put(4)  # [2, 3, 4] <- 1 evicted (oldest)

        # Thread 2 (consumer)
        q.pop()   # Returns 4 (most recent)
        q.pop()   # Returns 3
        q.pop()   # Returns 2
    """

    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:
        """
        Put an item into the queue (thread-safe).

        If the queue is full, automatically removes the oldest item first.
        Never blocks since space is always made available by eviction.

        The block and timeout parameters are accepted for API compatibility
        but are ignored since this implementation never blocks.

        Args:
            item: Item to add to the queue
            block: Ignored (kept for API compatibility)
            timeout: Ignored (kept for API compatibility)
        """
        with self.not_full:
            if self.maxsize > 0:
                # If at capacity, remove the oldest (bottom) item
                if self._qsize() >= self.maxsize:
                    self.queue.pop(0)  # Remove from bottom of stack
                    self.unfinished_tasks -= 1  # Adjust task counter

            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()

    def pop(self, block: bool = True, timeout: float | None = None) -> Any:
        """
        Remove and return an item from the queue (thread-safe, LIFO).

        Alias for get() to provide stack-like API. Returns the most recently
        added item (last in, first out).

        Args:
            block: If True (default), wait until an item is available.
                   If False, raise Empty immediately if queue is empty.
            timeout: Optional maximum seconds to wait for an item.
                     Only applies when block=True.
                     - None (default): wait forever
                     - float: wait up to this many seconds

        Returns:
            The most recently added item

        Raises:
            Empty: If block=False and queue is empty, or if timeout expires
                   while waiting for an item.

        Examples:
            item = q.pop()              # Wait forever for an item
            item = q.pop(block=False)   # Raise Empty if queue is empty
            item = q.pop(timeout=5.0)   # Wait up to 5 seconds
        """
        return self.get(block=block, timeout=timeout)
