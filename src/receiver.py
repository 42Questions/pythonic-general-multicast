"""UDP Receiver that listens for forwarded data."""

import json
import logging
import os
import socket
from collections.abc import Callable
from types import TracebackType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class Receiver:
    def __init__(self, listen_host: str, listen_port: int) -> None:
        self.listen_host: str = listen_host
        self.listen_port: int = listen_port
        self.sock: socket.socket | None = None
        self.last_spm: int = -1

    def __enter__(self) -> "Receiver":
        """Open the UDP socket when entering the context."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.listen_host, self.listen_port))
        self.last_spm = -1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Close the UDP socket when exiting the context."""
        if self.sock:
            self.sock.close()
        return False

    def receive_data(self, process_func: Callable[[dict], None]) -> None:
        """Receive UDP data and process it with the provided function."""
        if not self.sock:
            raise RuntimeError(
                "Socket not initialized. Use 'with Receiver(...) as receiver:' context manager."
            )

        _LOGGER.info(f"UDP Receiver started, listening on {self.listen_host}:{self.listen_port}")

        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                try:
                    message = data.decode("utf-8")
                    packet = json.loads(message)

                    # Check for packet loss
                    if "spm" in packet:
                        current_spm = packet["spm"]
                        if self.last_spm != -1 and current_spm != self.last_spm + 1:
                            lost_packets = current_spm - self.last_spm - 1
                            _LOGGER.warning(
                                f"Packet loss detected! Lost {lost_packets} packet(s). "
                                f"Last SPM: {self.last_spm}, Current SPM: {current_spm}"
                            )
                        self.last_spm = current_spm

                    _LOGGER.info(f"Received from {addr}: {message}")
                    process_func(packet)

                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    _LOGGER.error(f"Received invalid data from {addr}: {e}")
                    continue
        except KeyboardInterrupt:
            _LOGGER.info("Receiver stopped")


def main() -> None:
    """Listen for UDP data forwarded by the server."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5001"))

    def process_packet(packet: dict) -> None:
        """Process received packet - can be extended for custom logic."""
        if "data" in packet:
            _LOGGER.debug(f"Processing data: {packet['data']}")

    with Receiver(listen_host, listen_port) as receiver:
        receiver.receive_data(process_packet)


if __name__ == "__main__":
    main()
