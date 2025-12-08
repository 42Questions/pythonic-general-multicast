"""PGM Forwarder (Network Entity) that forwards packets and routes NAKs to DLR."""

import logging
import os
import socket
from types import TracebackType

from src.base import NetworkParticipant
from src.protocol import PacketType, PGMPacket

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class Forwarder(NetworkParticipant):
    """PGM Forwarder (Network Entity).

    Responsibilities:
    - Receive packets from upstream (sender)
    - Forward DATA/SPM packets to downstream (receivers and DLR)
    - Update SPM packets with own address before forwarding
    - Route NAKs from receivers to DLR
    - Broadcast repair DATA from DLR to all receivers
    """

    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        receiver_host: str,
        receiver_port: int,
        dlr_host: str,
        dlr_port: int,
        dlr_nak_host: str,
        dlr_nak_port: int,
        own_host: str,
        own_port: int,
    ) -> None:
        """Initialize PGM Forwarder.

        Args:
            listen_host: Host to listen for incoming packets from sender.
            listen_port: Port to listen for incoming packets from sender.
            receiver_host: Host to forward data to receivers.
            receiver_port: Port to forward data to receivers.
            dlr_host: DLR host to forward data to.
            dlr_port: DLR port to forward data to.
            dlr_nak_host: DLR host to forward NAKs to.
            dlr_nak_port: DLR port to forward NAKs to.
            own_host: This forwarder's address for SPM updates.
            own_port: This forwarder's port for SPM updates.
        """
        super().__init__()
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.receiver_host = receiver_host
        self.receiver_port = receiver_port
        self.dlr_host = dlr_host
        self.dlr_port = dlr_port
        self.dlr_nak_host = dlr_nak_host
        self.dlr_nak_port = dlr_nak_port
        self.own_host = own_host
        self.own_port = own_port
        self.forward_sock: socket.socket | None = None

    def __enter__(self) -> Forwarder:
        """Open UDP sockets when entering the context."""
        self.sock = self._create_socket()
        self.sock.bind((self.listen_host, self.listen_port))
        self.forward_sock = self._create_socket()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Close UDP sockets when exiting the context."""
        self._close_socket(self.sock)
        self._close_socket(self.forward_sock)
        return False

    def forward_data(self) -> None:
        """Receive and forward PGM packets.

        - DATA packets: broadcast to receivers and DLR
        - SPM packets: update last_hop and broadcast to receivers and DLR
        - NAK packets: forward to DLR for repair
        """
        if not self.sock or not self.forward_sock:
            raise RuntimeError(
                "Sockets not initialized. Use 'with Forwarder(...) as forwarder:' context manager."
            )

        _LOGGER.info(f"PGM Forwarder started, listening on {self.listen_host}:{self.listen_port}")
        _LOGGER.info(f"Forwarding to receivers: {self.receiver_host}:{self.receiver_port}")
        _LOGGER.info(f"Forwarding to DLR: {self.dlr_host}:{self.dlr_port}")
        _LOGGER.info(f"Forwarding NAKs to DLR: {self.dlr_nak_host}:{self.dlr_nak_port}")
        _LOGGER.info(f"Own address: {self.own_host}:{self.own_port}")

        try:
            while True:
                data, addr = self.sock.recvfrom(2048)
                try:
                    packet = PGMPacket.unpack(data)

                    if packet.packet_type == PacketType.DATA:
                        # Broadcast DATA to receivers and DLR
                        self.forward_sock.sendto(data, (self.receiver_host, self.receiver_port))
                        self.forward_sock.sendto(data, (self.dlr_host, self.dlr_port))
                        _LOGGER.info(f"Broadcast DATA: [SEQ: {packet.sequence}] from {addr}")

                    elif packet.packet_type == PacketType.SPM:
                        # Update SPM with our own address as last hop
                        updated_packet = PGMPacket(
                            packet_type=PacketType.SPM,
                            sequence=packet.sequence,
                            last_hop_host=self.own_host,
                            last_hop_port=self.own_port,
                        )
                        updated_data = updated_packet.pack()

                        # Broadcast updated SPM to receivers and DLR
                        self.forward_sock.sendto(
                            updated_data, (self.receiver_host, self.receiver_port)
                        )
                        self.forward_sock.sendto(updated_data, (self.dlr_host, self.dlr_port))
                        _LOGGER.info(
                            f"Broadcast SPM: [SEQ: {packet.sequence}] "
                            f"Updated path: {self.own_host}:{self.own_port}"
                        )

                    elif packet.packet_type == PacketType.NAK:
                        # Forward NAK to DLR
                        self.forward_sock.sendto(data, (self.dlr_nak_host, self.dlr_nak_port))
                        _LOGGER.info(
                            f"Forwarded NAK: [REQ SEQ: {packet.requested_sequence}] "
                            f"from {addr} to DLR"
                        )

                except (ValueError, OSError) as e:
                    _LOGGER.error(f"Error processing packet from {addr}: {e}")

        except KeyboardInterrupt:
            _LOGGER.info("Forwarder stopped")


def main() -> None:
    """Run PGM Forwarder."""
    listen_host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "5000"))
    receiver_host = os.environ.get("RECEIVER_HOST", "localhost")
    receiver_port = int(os.environ.get("RECEIVER_PORT", "5001"))
    dlr_host = os.environ.get("DLR_HOST", "localhost")
    dlr_port = int(os.environ.get("DLR_PORT", "5001"))
    dlr_nak_host = os.environ.get("DLR_NAK_HOST", "localhost")
    dlr_nak_port = int(os.environ.get("DLR_NAK_PORT", "5003"))
    own_host = os.environ.get("OWN_HOST", "localhost")
    own_port = int(os.environ.get("OWN_PORT", "5000"))

    with Forwarder(
        listen_host,
        listen_port,
        receiver_host,
        receiver_port,
        dlr_host,
        dlr_port,
        dlr_nak_host,
        dlr_nak_port,
        own_host,
        own_port,
    ) as forwarder:
        forwarder.forward_data()


if __name__ == "__main__":
    main()
