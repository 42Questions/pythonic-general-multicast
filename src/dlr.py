"""PGM DLR (Designated Local Repairer) that handles repair requests."""

import logging
import os
import socket
from types import TracebackType

from src.base import NetworkParticipant, RepairCache
from src.protocol import PacketType, PGMPacket, UserPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class DLR(NetworkParticipant):
    """PGM DLR (Designated Local Repairer).

    Responsibilities:
    - Receive DATA/SPM packets from forwarder (like a receiver)
    - Maintain repair cache of recent DATA packets
    - Listen for NAKs from forwarder
    - Send repair DATA back to forwarder for broadcast to all receivers
    """

    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        nak_listen_host: str,
        nak_listen_port: int,
        forwarder_host: str,
        forwarder_port: int,
        repair_cache_size: int = 100,
    ) -> None:
        """Initialize PGM DLR.

        Args:
            listen_host: Host to listen for DATA/SPM from forwarder.
            listen_port: Port to listen for DATA/SPM from forwarder.
            nak_listen_host: Host to listen for NAKs from forwarder.
            nak_listen_port: Port to listen for NAKs from forwarder.
            forwarder_host: Forwarder host to send repairs to.
            forwarder_port: Forwarder port to send repairs to.
            repair_cache_size: Size of repair cache (default: 100).
        """
        super().__init__()
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.nak_listen_host = nak_listen_host
        self.nak_listen_port = nak_listen_port
        self.forwarder_host = forwarder_host
        self.forwarder_port = forwarder_port
        self.repair_cache = RepairCache(max_size=repair_cache_size)
        self.nak_sock: socket.socket | None = None
        self.repair_sock: socket.socket | None = None
        self.last_spm = -1

    def __enter__(self) -> DLR:
        """Open UDP sockets when entering the context."""
        # Socket for receiving DATA/SPM
        self.sock = self._create_socket()
        self.sock.bind((self.listen_host, self.listen_port))

        # Socket for receiving NAKs
        self.nak_sock = self._create_socket()
        self.nak_sock.bind((self.nak_listen_host, self.nak_listen_port))
        self.nak_sock.settimeout(0.01)  # Very short timeout for non-blocking

        # Socket for sending repairs
        self.repair_sock = self._create_socket()

        self.last_spm = -1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Close UDP sockets when exiting the context."""
        self._close_socket(self.sock)
        self._close_socket(self.nak_sock)
        self._close_socket(self.repair_sock)
        return False

    def run(self, payload_handler: UserPayload | None = None) -> None:
        """Run DLR main loop.

        Args:
            payload_handler: Optional UserPayload instance to process received data.
        """
        if not self.sock or not self.nak_sock or not self.repair_sock:
            raise RuntimeError(
                "Sockets not initialized. Use 'with DLR(...) as dlr:' context manager."
            )

        _LOGGER.info(f"PGM DLR started, listening on {self.listen_host}:{self.listen_port}")
        _LOGGER.info(f"Listening for NAKs on {self.nak_listen_host}:{self.nak_listen_port}")

        try:
            while True:
                # Process incoming NAKs (non-blocking)
                self._process_naks()

                # Receive DATA/SPM packets
                try:
                    data, addr = self.sock.recvfrom(2048)
                    packet = PGMPacket.unpack(data)

                    if packet.packet_type == PacketType.DATA:
                        # Cache the packet for potential repair
                        self.repair_cache.add(packet.sequence, data)

                        # Update last sequence
                        self.last_spm = packet.sequence

                        # Optionally process payload
                        if payload_handler and packet.payload:
                            payload_handler.unpack(packet.payload)

                        _LOGGER.info(f"Cached DATA: [SEQ: {packet.sequence}] from {addr}")

                    elif packet.packet_type == PacketType.SPM:
                        _LOGGER.info(
                            f"Received SPM: [SEQ: {packet.sequence}] "
                            f"Last hop: {packet.last_hop_host}:{packet.last_hop_port}"
                        )

                except (ValueError, OSError) as e:
                    _LOGGER.error(f"Error receiving packet: {e}")

        except KeyboardInterrupt:
            _LOGGER.info("DLR stopped")

    def _process_naks(self) -> None:
        """Process incoming NAK requests and send repairs."""
        if not self.nak_sock or not self.repair_sock:
            return

        try:
            data, addr = self.nak_sock.recvfrom(1024)
            packet = PGMPacket.unpack(data)

            if packet.packet_type == PacketType.NAK:
                if packet.requested_sequence is None:
                    _LOGGER.warning(f"Received NAK from {addr} with no requested sequence")
                    return

                _LOGGER.info(f"Received NAK from {addr} for SEQ: {packet.requested_sequence}")

                # Check if we have the requested packet in cache
                repair_data = self.repair_cache.get(packet.requested_sequence)
                if repair_data:
                    # Send repair to forwarder for broadcast
                    self.repair_sock.sendto(repair_data, (self.forwarder_host, self.forwarder_port))
                    _LOGGER.info(f"Sent repair for SEQ: {packet.requested_sequence} to forwarder")
                else:
                    _LOGGER.warning(
                        f"Cannot repair SEQ: {packet.requested_sequence} - not in cache"
                    )

        except TimeoutError:
            # No NAK received, continue
            pass
        except (ValueError, OSError) as e:
            _LOGGER.error(f"Error processing NAK: {e}")


class IntPayload(UserPayload):
    """Example user payload that packs/unpacks a single integer."""

    def __init__(self, value: int = 0) -> None:
        """Initialize with an integer value.

        Args:
            value: Integer value to store.
        """
        self.value = value

    def pack(self) -> bytes:
        """Pack integer to bytes (4 bytes, big endian).

        Returns:
            bytes: Packed integer.
        """
        return self.value.to_bytes(4, byteorder="big", signed=True)

    def unpack(self, data: bytes) -> None:
        """Unpack bytes to integer.

        Args:
            data: Raw bytes to unpack.
        """
        if len(data) < 4:
            raise ValueError(f"Expected at least 4 bytes, got {len(data)}")
        self.value = int.from_bytes(data[:4], byteorder="big", signed=True)


def main() -> None:
    """Run DLR to cache data and handle repair requests."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5001"))
    nak_listen_host = os.environ.get("NAK_LISTEN_HOST", "0.0.0.0")
    nak_listen_port = int(os.environ.get("NAK_LISTEN_PORT", "5003"))
    forwarder_host = os.environ.get("FORWARDER_HOST", "localhost")
    forwarder_port = int(os.environ.get("FORWARDER_PORT", "5000"))
    repair_cache_size = int(os.environ.get("REPAIR_CACHE_SIZE", "100"))

    payload = IntPayload()

    with DLR(
        listen_host,
        listen_port,
        nak_listen_host,
        nak_listen_port,
        forwarder_host,
        forwarder_port,
        repair_cache_size,
    ) as dlr:
        dlr.run(payload)


if __name__ == "__main__":
    main()
