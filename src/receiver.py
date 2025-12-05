"""UDP Receiver that listens for forwarded data."""

import logging
import os
import socket

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


def main():
    """Listen for UDP data forwarded by the server."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5001"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_host, listen_port))

    _LOGGER.info(f"UDP Receiver started, listening on {listen_host}:{listen_port}")

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            try:
                message = data.decode("utf-8")
            except UnicodeDecodeError:
                _LOGGER.error(f"Received invalid UTF-8 data from {addr}")
                continue
            _LOGGER.info(f"Received from {addr}: {message}")
    except KeyboardInterrupt:
        _LOGGER.info("Receiver stopped")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
