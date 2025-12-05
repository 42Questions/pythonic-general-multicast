"""UDP Server that receives data and forwards it to another socket."""

import logging
import os
import socket
from collections.abc import Callable
from types import TracebackType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class Forwarder:
    def __init__(
        self, listen_host: str, listen_port: int, forward_host: str, forward_port: int
    ) -> None:
        self.listen_host: str = listen_host
        self.listen_port: int = listen_port
        self.forward_host: str = forward_host
        self.forward_port: int = forward_port
        self.listen_sock: socket.socket | None = None
        self.forward_sock: socket.socket | None = None

    def __enter__(self) -> "Forwarder":
        """Open the UDP sockets when entering the context."""
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_sock.bind((self.listen_host, self.listen_port))
        self.forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Close the UDP sockets when exiting the context."""
        if self.listen_sock:
            self.listen_sock.close()
        if self.forward_sock:
            self.forward_sock.close()
        return False

    def forward_data(self, process_func: Callable[[bytes, tuple], bytes]) -> None:
        """Receive UDP data, process it, and forward to destination."""
        if not self.listen_sock or not self.forward_sock:
            raise RuntimeError(
                "Sockets not initialized. Use 'with Forwarder(...) as forwarder:' context manager."
            )

        _LOGGER.info(f"UDP Server started, listening on {self.listen_host}:{self.listen_port}")
        _LOGGER.info(f"Forwarding to {self.forward_host}:{self.forward_port}")

        try:
            while True:
                data, addr = self.listen_sock.recvfrom(1024)
                try:
                    # Process the raw data
                    processed_data = process_func(data, addr)

                    # Forward the processed data
                    self.forward_sock.sendto(processed_data, (self.forward_host, self.forward_port))
                except OSError as e:
                    _LOGGER.error(f"Failed to forward: {e}")
        except KeyboardInterrupt:
            _LOGGER.info("Server stopped")


def main() -> None:
    """Receive UDP data and forward it to another destination."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5000"))
    forward_host = os.environ.get("FORWARD_HOST", "localhost")
    forward_port = int(os.environ.get("FORWARD_PORT", "5001"))

    with Forwarder(listen_host, listen_port, forward_host, forward_port) as forwarder:
        forwarder.forward_data(lambda data, addr: data)


if __name__ == "__main__":
    main()
