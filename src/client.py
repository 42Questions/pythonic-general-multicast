"""UDP Client that sends random numbers to a server."""

import json
import logging
import os
import random
import socket
import time
from collections.abc import Callable
from types import TracebackType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class Sender:
    def __init__(self, server_host: str, server_port: int, send_interval: float) -> None:
        self.server_host: str = server_host
        self.server_port: int = server_port
        self.send_interval: float = send_interval
        self.sock: socket.socket | None = None
        self.sequence_number: int = 0

    def __enter__(self) -> Sender:
        """Open the UDP socket when entering the context."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sequence_number = 0
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

    def send_data(self, send_func: Callable[[], int]) -> None:
        """Send data using the provided send function at regular intervals."""
        if not self.sock:
            raise RuntimeError(
                "Socket not initialized. Use 'with Sender(...) as sender:' context manager."
            )

        _LOGGER.info(f"UDP Client started, sending to {self.server_host}:{self.server_port}")

        try:
            while True:
                data = send_func()
                packet = {"spm": self.sequence_number, "data": data}
                message = json.dumps(packet).encode("utf-8")
                try:
                    self.sock.sendto(message, (self.server_host, self.server_port))
                    _LOGGER.info(f"Sent: [SPM: {self.sequence_number}] {data}")
                    self.sequence_number += 1
                except OSError as e:
                    _LOGGER.error(f"Failed to send: {e}")
                time.sleep(self.send_interval)
        except KeyboardInterrupt:
            _LOGGER.info("Client stopped")


def main():
    """Send random numbers to the UDP server."""
    server_host = os.environ.get("SERVER_HOST", "localhost")
    server_port = int(os.environ.get("SERVER_PORT", "5000"))
    send_interval = float(os.environ.get("SEND_INTERVAL", "1.0"))

    with Sender(server_host, server_port, send_interval) as sender:
        sender.send_data(lambda: random.randint(1, 10))


if __name__ == "__main__":
    main()
