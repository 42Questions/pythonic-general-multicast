"""UDP Server that receives data and forwards it to another socket."""

import os
import socket


def main():
    """Receive UDP data and forward it to another destination."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5000"))
    forward_host = os.environ.get("FORWARD_HOST", "localhost")
    forward_port = int(os.environ.get("FORWARD_PORT", "5001"))

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind((listen_host, listen_port))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"UDP Server started, listening on {listen_host}:{listen_port}")
    print(f"Forwarding to {forward_host}:{forward_port}")

    try:
        while True:
            data, addr = recv_sock.recvfrom(1024)
            message = data.decode("utf-8")
            print(f"Received from {addr}: {message}")

            send_sock.sendto(data, (forward_host, forward_port))
            print(f"Forwarded: {message}")
    except KeyboardInterrupt:
        print("Server stopped")
    finally:
        recv_sock.close()
        send_sock.close()


if __name__ == "__main__":
    main()
