"""PGM Receiver (End Client) that receives data and sends NAKs for missing packets."""

import logging
import os
import socket
from types import TracebackType

from src.base import NetworkParticipant
from src.protocol import PacketType, PGMPacket, UserPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class Receiver(NetworkParticipant):
    """PGM Receiver (End Client).

    Responsibilities:
    - Receive DATA packets and extract user payload
    - Track sequence numbers to detect packet loss
    - Send NAKs for missing packets to last known hop
    - Process SPM packets to learn network topology
    """

    def __init__(self, listen_host: str, listen_port: int) -> None:
        """Initialize PGM Receiver.

        Args:
            listen_host: Host to listen for incoming packets.
            listen_port: Port to listen for incoming packets.
        """
        super().__init__()
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.last_spm = -1
        self.last_hop_host: str | None = None
        self.last_hop_port: int | None = None
        self.nak_sock: socket.socket | None = None

    def __enter__(self) -> Receiver:
        """Open UDP sockets when entering the context."""
        self.sock = self._create_socket()
        self.sock.bind((self.listen_host, self.listen_port))
        self.nak_sock = self._create_socket()
        self.last_spm = -1
        self.last_hop_host = None
        self.last_hop_port = None
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
        return False

    def receive_data(self, payload_handler: UserPayload) -> None:
        """Receive PGM packets and process user data.

        Args:
            payload_handler: UserPayload instance to unpack received data.
        """
        if not self.sock or not self.nak_sock:
            raise RuntimeError(
                "Sockets not initialized. Use 'with Receiver(...) as receiver:' context manager."
            )

        _LOGGER.info(f"PGM Receiver started, listening on {self.listen_host}:{self.listen_port}")

        try:
            while True:
                data, addr = self.sock.recvfrom(2048)
                try:
                    packet = PGMPacket.unpack(data)

                    if packet.packet_type == PacketType.DATA:
                        # Check for packet loss
                        if self.last_spm != -1 and packet.sequence != self.last_spm + 1:
                            # Packets were lost
                            lost_count = packet.sequence - self.last_spm - 1
                            _LOGGER.warning(
                                f"Packet loss detected! Lost {lost_count} packet(s). "
                                f"Last SEQ: {self.last_spm}, Current SEQ: {packet.sequence}"
                            )

                            # Send NAKs for each missing sequence
                            if self.last_hop_host and self.last_hop_port:
                                for missing_seq in range(self.last_spm + 1, packet.sequence):
                                    self._send_nak(missing_seq)
                            else:
                                _LOGGER.warning("Cannot send NAK: unknown upstream address")

                        # Update last sequence
                        self.last_spm = packet.sequence

                        # Unpack and process payload
                        if packet.payload:
                            payload_handler.unpack(packet.payload)
                            _LOGGER.info(f"Received DATA: [SEQ: {packet.sequence}] from {addr}")
                        else:
                            _LOGGER.warning(
                                f"Received DATA with no payload: [SEQ: {packet.sequence}]"
                            )

                    elif packet.packet_type == PacketType.SPM:
                        # Update topology information
                        self.last_hop_host = packet.last_hop_host
                        self.last_hop_port = packet.last_hop_port
                        _LOGGER.info(
                            f"Received SPM: [SEQ: {packet.sequence}] "
                            f"Last hop: {self.last_hop_host}:{self.last_hop_port}"
                        )

                    elif packet.packet_type == PacketType.NAK:
                        # Receivers don't process NAKs
                        _LOGGER.debug(f"Ignoring NAK packet from {addr}")

                except (ValueError, OSError) as e:
                    _LOGGER.error(f"Error processing packet from {addr}: {e}")

        except KeyboardInterrupt:
            _LOGGER.info("Receiver stopped")

    def _send_nak(self, missing_sequence: int) -> None:
        """Send NAK for a missing sequence number.

        Args:
            missing_sequence: Sequence number to request.
        """
        if not self.nak_sock or not self.last_hop_host or not self.last_hop_port:
            return

        nak_packet = PGMPacket(
            packet_type=PacketType.NAK,
            sequence=0,  # NAK sequence doesn't matter for this implementation
            requested_sequence=missing_sequence,
        )
        nak_bytes = nak_packet.pack()

        try:
            self.nak_sock.sendto(nak_bytes, (self.last_hop_host, self.last_hop_port))
            _LOGGER.info(
                f"Sent NAK for SEQ: {missing_sequence} to {self.last_hop_host}:{self.last_hop_port}"
            )
        except OSError as e:
            _LOGGER.error(f"Failed to send NAK: {e}")


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
    """Listen for PGM data and print received integers."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5001"))

    payload = IntPayload()

    with Receiver(listen_host, listen_port) as receiver:
        receiver.receive_data(payload)


if __name__ == "__main__":
    main()
