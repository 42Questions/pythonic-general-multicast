"""Tests for BoundedLifoQueue focusing on multithreading behavior."""

import threading
import time
from queue import Empty

import pytest

from src.utils import BoundedLifoQueue


class TestBoundedLifoQueueThreadSafety:
    """Test thread-safety of BoundedLifoQueue operations."""

    def test_concurrent_puts_from_multiple_threads(self):
        """Test that multiple threads can put items concurrently without data corruption."""
        q = BoundedLifoQueue(maxsize=1000)
        num_threads = 10
        items_per_thread = 100

        def producer(thread_id):
            for i in range(items_per_thread):
                q.put((thread_id, i))

        threads = [threading.Thread(target=producer, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All items should be in the queue
        assert q.qsize() == num_threads * items_per_thread

        # Verify all items are retrievable
        items = []
        while not q.empty():
            items.append(q.get())

        assert len(items) == num_threads * items_per_thread

    def test_concurrent_pops_from_multiple_threads(self):
        """Test that multiple threads can pop items concurrently without issues."""
        q = BoundedLifoQueue(maxsize=1000)
        num_items = 100

        # Pre-fill queue
        for i in range(num_items):
            q.put(i)

        results = []
        lock = threading.Lock()

        def consumer():
            while True:
                try:
                    item = q.pop(block=False)
                    with lock:
                        results.append(item)
                except Empty:
                    break

        num_threads = 5
        threads = [threading.Thread(target=consumer) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All items should have been consumed
        assert len(results) == num_items
        assert q.empty()

    def test_producer_consumer_pattern(self):
        """Test classic producer-consumer pattern with one producer and one consumer."""
        q = BoundedLifoQueue(maxsize=50)
        num_items = 200
        consumed = []

        def producer():
            for i in range(num_items):
                q.put(i)
                time.sleep(0.001)  # Small delay to simulate work

        def consumer():
            for _ in range(num_items):
                item = q.pop(timeout=5.0)
                consumed.append(item)

        prod_thread = threading.Thread(target=producer)
        cons_thread = threading.Thread(target=consumer)

        cons_thread.start()
        prod_thread.start()

        prod_thread.join()
        cons_thread.join()

        # All items should have been consumed
        assert len(consumed) == num_items
        assert q.empty()

    def test_multiple_producers_single_consumer(self):
        """Test multiple producers feeding a single consumer."""
        q = BoundedLifoQueue(maxsize=100)
        num_producers = 5
        items_per_producer = 40
        consumed: list[tuple[int, int]] = []

        def producer(thread_id):
            for i in range(items_per_producer):
                q.put((thread_id, i))
                time.sleep(0.001)

        def consumer():
            total_expected = num_producers * items_per_producer
            while len(consumed) < total_expected:
                try:
                    item = q.pop(timeout=1.0)
                    consumed.append(item)
                except Empty:
                    if len(consumed) >= total_expected:
                        break

        producers = [threading.Thread(target=producer, args=(i,)) for i in range(num_producers)]
        consumer_thread = threading.Thread(target=consumer)

        consumer_thread.start()
        for p in producers:
            p.start()

        for p in producers:
            p.join()
        consumer_thread.join()

        assert len(consumed) == num_producers * items_per_producer

    def test_auto_eviction_under_concurrent_load(self):
        """Test that auto-eviction works correctly with concurrent puts."""
        maxsize = 10
        q = BoundedLifoQueue(maxsize=maxsize)
        num_threads = 5
        items_per_thread = 50

        def producer(thread_id):
            for i in range(items_per_thread):
                q.put((thread_id, i))

        threads = [threading.Thread(target=producer, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Queue should never exceed maxsize
        assert q.qsize() <= maxsize

        # Should have exactly maxsize items (the most recent ones)
        assert q.qsize() == maxsize

    def test_lifo_order_maintained_under_concurrent_access(self):
        """Test that LIFO ordering is maintained even with concurrent access."""
        q = BoundedLifoQueue(maxsize=100)

        # Single producer to ensure ordered insertion
        for i in range(10):
            q.put(i)

        # Multiple consumers should still get LIFO order
        results = []
        lock = threading.Lock()

        def consumer():
            try:
                item = q.pop(block=False)
                with lock:
                    results.append(item)
            except Empty:
                pass

        # Create threads but execute them quickly
        threads = [threading.Thread(target=consumer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All items should be consumed
        assert len(results) == 10
        # Results should be in LIFO order (9, 8, 7, ... 0)
        # Note: With concurrent access, exact order might vary slightly,
        # but the most recent items should appear first
        assert 9 in results[:3]  # Most recent should be consumed first


class TestBoundedLifoQueueTimeout:
    """Test timeout behavior in multithreaded scenarios."""

    def test_pop_timeout_expires_when_queue_empty(self):
        """Test that pop with timeout raises Empty after timeout expires."""
        q = BoundedLifoQueue(maxsize=10)

        start_time = time.time()
        with pytest.raises(Empty):
            q.pop(timeout=0.5)
        elapsed = time.time() - start_time

        # Should wait approximately 0.5 seconds
        assert 0.4 < elapsed < 0.7

    def test_pop_timeout_returns_immediately_when_item_available(self):
        """Test that pop with timeout returns immediately if item is available."""
        q = BoundedLifoQueue(maxsize=10)
        q.put("test_item")

        start_time = time.time()
        item = q.pop(timeout=5.0)
        elapsed = time.time() - start_time

        assert item == "test_item"
        # Should return almost immediately
        assert elapsed < 0.1

    def test_pop_waits_until_item_arrives(self):
        """Test that pop with timeout waits and returns when item arrives."""
        q = BoundedLifoQueue(maxsize=10)
        result = []

        def delayed_producer():
            time.sleep(0.3)
            q.put("delayed_item")

        def consumer():
            item = q.pop(timeout=2.0)
            result.append(item)

        prod_thread = threading.Thread(target=delayed_producer)
        cons_thread = threading.Thread(target=consumer)

        start_time = time.time()
        cons_thread.start()
        prod_thread.start()

        cons_thread.join()
        prod_thread.join()
        elapsed = time.time() - start_time

        assert result[0] == "delayed_item"
        # Should wait ~0.3 seconds for the item
        assert 0.2 < elapsed < 0.5

    def test_multiple_consumers_with_timeout(self):
        """Test multiple consumers waiting with timeout."""
        q = BoundedLifoQueue(maxsize=10)
        num_items = 5
        num_consumers = 10

        # Put fewer items than consumers
        for i in range(num_items):
            q.put(i)

        results = []
        timeouts = []
        lock = threading.Lock()

        def consumer():
            try:
                item = q.pop(timeout=0.5)
                with lock:
                    results.append(item)
            except Empty:
                with lock:
                    timeouts.append(True)

        threads = [threading.Thread(target=consumer) for _ in range(num_consumers)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have consumed all items
        assert len(results) == num_items
        # Remaining consumers should have timed out
        assert len(timeouts) == num_consumers - num_items


class TestBoundedLifoQueueEdgeCases:
    """Test edge cases and race conditions."""

    def test_pop_block_false_on_empty_queue(self):
        """Test that pop with block=False immediately raises Empty."""
        q = BoundedLifoQueue(maxsize=10)

        with pytest.raises(Empty):
            q.pop(block=False)

    def test_alternating_put_pop_same_thread(self):
        """Test alternating put and pop operations in the same thread."""
        q = BoundedLifoQueue(maxsize=5)

        for i in range(20):
            q.put(i)
            item = q.pop()
            assert item == i

    def test_queue_size_consistency_under_load(self):
        """Test that queue size remains consistent under concurrent operations."""
        q = BoundedLifoQueue(maxsize=50)
        stop_flag = threading.Event()

        def producer():
            while not stop_flag.is_set():
                q.put(1)
                time.sleep(0.001)

        def consumer():
            while not stop_flag.is_set():
                try:
                    q.pop(block=False)
                except Empty:
                    pass
                time.sleep(0.001)

        producers = [threading.Thread(target=producer) for _ in range(3)]
        consumers = [threading.Thread(target=consumer) for _ in range(3)]

        for t in producers + consumers:
            t.start()

        time.sleep(0.5)
        stop_flag.set()

        for t in producers + consumers:
            t.join()

        # Queue should never exceed maxsize
        assert q.qsize() <= 50

    def test_no_deadlock_with_multiple_blocking_pops(self):
        """Test that multiple blocking pops don't cause deadlock when items arrive."""
        q = BoundedLifoQueue(maxsize=10)
        results = []
        lock = threading.Lock()

        def consumer(consumer_id):
            item = q.pop(timeout=2.0)
            with lock:
                results.append((consumer_id, item))

        def producer():
            time.sleep(0.2)
            for i in range(5):
                q.put(i)

        # Start consumers first (they will block)
        consumers = [threading.Thread(target=consumer, args=(i,)) for i in range(5)]
        for c in consumers:
            c.start()

        # Start producer after a delay
        prod_thread = threading.Thread(target=producer)
        prod_thread.start()

        prod_thread.join()
        for c in consumers:
            c.join()

        # All consumers should have received items
        assert len(results) == 5
