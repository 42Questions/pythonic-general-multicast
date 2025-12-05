"""UDP Receiver that listens for forwarded data."""

import os
import socket


def main():
    """Listen for UDP data forwarded by the server."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5001"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_host, listen_port))

    print(f"UDP Receiver started, listening on {listen_host}:{listen_port}")

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            message = data.decode("utf-8")
            print(f"Received from {addr}: {message}")
    except KeyboardInterrupt:
        print("Receiver stopped")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
