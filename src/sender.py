"""PGM Sender (Primary Source) that sends data packets."""

import logging
import os
import random
import time
from types import TracebackType

from src.base import NetworkParticipant
from src.protocol import PacketType, PGMPacket, UserPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class Sender(NetworkParticipant):
    """PGM Sender (Primary Source).

    Responsibilities:
    - Send DATA packets with user payload
    - Send periodic SPM packets for topology discovery

    Note: Repair/NAK handling is delegated to DLR (Designated Local Repairer).
    """

    def __init__(
        self,
        server_host: str,
        server_port: int,
        own_host: str,
        own_port: int,
        send_interval: float,
        spm_interval: float = 5.0,
    ) -> None:
        """Initialize PGM Sender.

        Args:
            server_host: Server/forwarder host to send data to.
            server_port: Server/forwarder port to send data to.
            own_host: This sender's address for SPM.
            own_port: This sender's port for SPM.
            send_interval: Interval between DATA packets (seconds).
            spm_interval: Interval between SPM packets (seconds).
        """
        super().__init__()
        self.server_host = server_host
        self.server_port = server_port
        self.own_host = own_host
        self.own_port = own_port
        self.send_interval = send_interval
        self.spm_interval = spm_interval
        self.sequence_number = 0
        self.last_spm_time = 0.0

    def __enter__(self) -> Sender:
        """Open UDP socket when entering the context."""
        self.sock = self._create_socket()
        self.sequence_number = 0
        self.last_spm_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Close UDP socket when exiting the context."""
        self._close_socket(self.sock)
        return False

    def send_data(self, payload_generator: UserPayload) -> None:
        """Send DATA packets with user payload at regular intervals.

        Args:
            payload_generator: UserPayload instance that generates data to send.
        """
        if not self.sock:
            raise RuntimeError(
                "Socket not initialized. Use 'with Sender(...) as sender:' context manager."
            )

        _LOGGER.info(f"PGM Sender started, sending to {self.server_host}:{self.server_port}")

        try:
            while True:
                # Send periodic SPM
                current_time = time.time()
                if current_time - self.last_spm_time >= self.spm_interval:
                    self._send_spm()
                    self.last_spm_time = current_time

                # Send DATA packet
                payload_bytes = payload_generator.pack()
                packet = PGMPacket(
                    packet_type=PacketType.DATA,
                    sequence=self.sequence_number,
                    payload=payload_bytes,
                )
                packet_bytes = packet.pack()

                try:
                    self.sock.sendto(packet_bytes, (self.server_host, self.server_port))
                    _LOGGER.info(f"Sent DATA: [SEQ: {self.sequence_number}]")
                    self.sequence_number += 1

                except OSError as e:
                    _LOGGER.error(f"Failed to send DATA: {e}")

                time.sleep(self.send_interval)

        except KeyboardInterrupt:
            _LOGGER.info("Sender stopped")

    def _send_spm(self) -> None:
        """Send SPM (Source Path Message) packet."""
        if not self.sock:
            return

        packet = PGMPacket(
            packet_type=PacketType.SPM,
            sequence=self.sequence_number,
            last_hop_host=self.own_host,
            last_hop_port=self.own_port,
        )
        packet_bytes = packet.pack()

        try:
            self.sock.sendto(packet_bytes, (self.server_host, self.server_port))
            _LOGGER.info(
                f"Sent SPM: [SEQ: {self.sequence_number}] Path: {self.own_host}:{self.own_port}"
            )
        except OSError as e:
            _LOGGER.error(f"Failed to send SPM: {e}")


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
    """Send random integers to the PGM network."""
    server_host = os.environ.get("SERVER_HOST", "localhost")
    server_port = int(os.environ.get("SERVER_PORT", "5000"))
    own_host = os.environ.get("OWN_HOST", "localhost")
    own_port = int(os.environ.get("OWN_PORT", "5000"))
    send_interval = float(os.environ.get("SEND_INTERVAL", "1.0"))
    spm_interval = float(os.environ.get("SPM_INTERVAL", "5.0"))

    with Sender(
        server_host, server_port, own_host, own_port, send_interval, spm_interval
    ) as sender:
        # Create a payload generator that produces random integers
        payload = IntPayload()

        class PayloadGenerator(UserPayload):
            def pack(self) -> bytes:
                payload.value = random.randint(1, 100)
                return payload.pack()

            def unpack(self, data: bytes) -> None:
                payload.unpack(data)

        sender.send_data(PayloadGenerator())


if __name__ == "__main__":
    main()
