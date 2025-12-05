"""UDP Client that sends random numbers to a server."""

import os
import random
import socket
import time


def main():
    """Send random numbers to the UDP server."""
    server_host = os.environ.get("SERVER_HOST", "localhost")
    server_port = int(os.environ.get("SERVER_PORT", "5000"))
    send_interval = float(os.environ.get("SEND_INTERVAL", "1.0"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"UDP Client started, sending to {server_host}:{server_port}")

    try:
        while True:
            random_number = random.randint(1, 1000)
            message = f"{random_number}".encode("utf-8")
            try:
                sock.sendto(message, (server_host, server_port))
                print(f"Sent: {random_number}")
            except OSError as e:
                print(f"Failed to send: {e}")
            time.sleep(send_interval)
    except KeyboardInterrupt:
        print("Client stopped")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
