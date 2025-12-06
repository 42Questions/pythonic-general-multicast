"""Base classes for PGM network participants."""

import socket
from abc import ABC, abstractmethod
from collections import deque
from types import TracebackType


class NetworkParticipant(ABC):
    """Abstract base class for PGM network participants.

    All participants (Sender, Forwarder, Receiver) share:
    - Socket lifecycle management
    - Understanding of PGM packet protocol
    - Knowledge of packet structure
    """

    def __init__(self) -> None:
        """Initialize network participant."""
        self.sock: socket.socket | None = None

    @abstractmethod
    def __enter__(self) -> NetworkParticipant:
        """Enter context manager - setup sockets."""
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Exit context manager - cleanup sockets."""
        pass

    def _create_socket(self) -> socket.socket:
        """Create a UDP socket.

        Returns:
            socket.socket: New UDP socket.
        """
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _close_socket(self, sock: socket.socket | None) -> None:
        """Close a socket if it exists.

        Args:
            sock: Socket to close.
        """
        if sock:
            sock.close()


class RepairCache:
    """Fixed-size cache for repair data packets.

    Stores the most recent N DATA packets for NAK repair requests.
    """

    def __init__(self, max_size: int = 100) -> None:
        """Initialize repair cache.

        Args:
            max_size: Maximum number of packets to cache (default: 100).
        """
        self.max_size = max_size
        self._cache: deque[tuple[int, bytes]] = deque(maxlen=max_size)
        self._min_sequence: int = 0

    def add(self, sequence: int, packet_data: bytes) -> None:
        """Add a packet to the cache.

        Args:
            sequence: Sequence number of the packet.
            packet_data: Serialized packet bytes.
        """
        self._cache.append((sequence, packet_data))
        if len(self._cache) == self.max_size:
            self._min_sequence = self._cache[0][0]

    def get(self, sequence: int) -> bytes | None:
        """Retrieve a packet from the cache by sequence number.

        Args:
            sequence: Sequence number to retrieve.

        Returns:
            bytes | None: Serialized packet bytes if found, None otherwise.
        """
        for seq, data in self._cache:
            if seq == sequence:
                return data
        return None

    def has_sequence(self, sequence: int) -> bool:
        """Check if a sequence number is available in the cache.

        Args:
            sequence: Sequence number to check.

        Returns:
            bool: True if sequence is in cache, False otherwise.
        """
        if not self._cache:
            return False
        return self._min_sequence <= sequence <= self._cache[-1][0]
