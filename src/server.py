"""UDP Server that receives data and forwards it to another socket."""

import logging
import os
import socket

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


def main():
    """Receive UDP data and forward it to another destination."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5000"))
    forward_host = os.environ.get("FORWARD_HOST", "localhost")
    forward_port = int(os.environ.get("FORWARD_PORT", "5001"))

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind((listen_host, listen_port))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    _LOGGER.info(f"UDP Server started, listening on {listen_host}:{listen_port}")
    _LOGGER.info(f"Forwarding to {forward_host}:{forward_port}")

    try:
        while True:
            data, addr = recv_sock.recvfrom(1024)
            try:
                message = data.decode("utf-8")
            except UnicodeDecodeError:
                _LOGGER.error(f"Received invalid UTF-8 data from {addr}")
                continue

            _LOGGER.info(f"Received from {addr}: {message}")

            try:
                send_sock.sendto(data, (forward_host, forward_port))
                _LOGGER.info(f"Forwarded: {message}")
            except OSError as e:
                _LOGGER.error(f"Failed to forward: {e}")
    except KeyboardInterrupt:
        _LOGGER.info("Server stopped")
    finally:
        recv_sock.close()
        send_sock.close()


if __name__ == "__main__":
    main()
