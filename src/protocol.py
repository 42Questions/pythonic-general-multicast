"""PGM protocol packet definitions and base classes."""

import struct
from abc import ABC, abstractmethod
from enum import IntEnum


class PacketType(IntEnum):
    """PGM packet types."""

    SPM = 0  # Source Path Message
    NAK = 1  # Negative Acknowledgement
    DATA = 2  # Data packet


class UserPayload(ABC):
    """Abstract base class for user-defined payload."""

    @abstractmethod
    def pack(self) -> bytes:
        """Serialize payload to bytes.

        Returns:
            bytes: Serialized payload data.
        """
        pass

    @abstractmethod
    def unpack(self, data: bytes) -> None:
        """Deserialize bytes into payload.

        Args:
            data: Raw bytes to deserialize.
        """
        pass


class PGMPacket:
    """PGM packet with header and optional payload.

    Packet structure (all fields in network byte order - big endian):
    - Packet type (1 byte)
    - Sequence number (4 bytes, uint32)
    - Type-specific fields:
        - SPM: last_hop_host (4 bytes IPv4), last_hop_port (2 bytes uint16)
        - NAK: requested_sequence (4 bytes uint32)
        - DATA: payload (variable length bytes)
    """

    # Header format for common fields: type (B) + sequence (I)
    COMMON_HEADER_FORMAT = "!BI"  # ! = network byte order (big endian)
    COMMON_HEADER_SIZE = struct.calcsize(COMMON_HEADER_FORMAT)

    # SPM additional fields: IPv4 address (I) + port (H)
    SPM_FORMAT = "!IH"
    SPM_SIZE = struct.calcsize(SPM_FORMAT)

    # NAK additional fields: requested sequence (I)
    NAK_FORMAT = "!I"
    NAK_SIZE = struct.calcsize(NAK_FORMAT)

    def __init__(
        self,
        packet_type: PacketType,
        sequence: int,
        last_hop_host: str | None = None,
        last_hop_port: int | None = None,
        requested_sequence: int | None = None,
        payload: bytes | None = None,
    ) -> None:
        """Initialize PGM packet.

        Args:
            packet_type: Type of packet (SPM, NAK, DATA).
            sequence: Sequence number.
            last_hop_host: For SPM packets, the last hop IPv4 address.
            last_hop_port: For SPM packets, the last hop port.
            requested_sequence: For NAK packets, the requested sequence number.
            payload: For DATA packets, the user payload bytes.
        """
        self.packet_type = packet_type
        self.sequence = sequence
        self.last_hop_host = last_hop_host
        self.last_hop_port = last_hop_port
        self.requested_sequence = requested_sequence
        self.payload = payload

    def pack(self) -> bytes:
        """Pack packet into bytes with network byte order.

        Returns:
            bytes: Serialized packet.
        """
        # Pack common header
        data = struct.pack(self.COMMON_HEADER_FORMAT, self.packet_type, self.sequence)

        if self.packet_type == PacketType.SPM:
            if self.last_hop_host is None or self.last_hop_port is None:
                raise ValueError("SPM packet requires last_hop_host and last_hop_port")
            # Convert IPv4 string to 32-bit integer
            host_int = self._ipv4_to_int(self.last_hop_host)
            data += struct.pack(self.SPM_FORMAT, host_int, self.last_hop_port)

        elif self.packet_type == PacketType.NAK:
            if self.requested_sequence is None:
                raise ValueError("NAK packet requires requested_sequence")
            data += struct.pack(self.NAK_FORMAT, self.requested_sequence)

        elif self.packet_type == PacketType.DATA:
            if self.payload is None:
                raise ValueError("DATA packet requires payload")
            data += self.payload

        return data

    @classmethod
    def unpack(cls, data: bytes) -> PGMPacket:
        """Unpack bytes into PGM packet with network byte order conversion.

        Args:
            data: Raw packet bytes.

        Returns:
            PGMPacket: Deserialized packet.
        """
        if len(data) < cls.COMMON_HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} bytes")

        # Unpack common header
        packet_type_int, sequence = struct.unpack(
            cls.COMMON_HEADER_FORMAT, data[: cls.COMMON_HEADER_SIZE]
        )
        packet_type = PacketType(packet_type_int)

        offset = cls.COMMON_HEADER_SIZE

        if packet_type == PacketType.SPM:
            if len(data) < cls.COMMON_HEADER_SIZE + cls.SPM_SIZE:
                raise ValueError("SPM packet too short")
            host_int, port = struct.unpack(cls.SPM_FORMAT, data[offset : offset + cls.SPM_SIZE])
            host = cls._int_to_ipv4(host_int)
            return cls(
                packet_type=packet_type,
                sequence=sequence,
                last_hop_host=host,
                last_hop_port=port,
            )

        elif packet_type == PacketType.NAK:
            if len(data) < cls.COMMON_HEADER_SIZE + cls.NAK_SIZE:
                raise ValueError("NAK packet too short")
            (requested_seq,) = struct.unpack(cls.NAK_FORMAT, data[offset : offset + cls.NAK_SIZE])
            return cls(
                packet_type=packet_type,
                sequence=sequence,
                requested_sequence=requested_seq,
            )

        elif packet_type == PacketType.DATA:
            payload = data[offset:]
            return cls(packet_type=packet_type, sequence=sequence, payload=payload)

        else:
            raise ValueError(f"Unknown packet type: {packet_type}")

    @staticmethod
    def _ipv4_to_int(ipv4: str) -> int:
        """Convert IPv4 string to 32-bit integer.

        Args:
            ipv4: IPv4 address string (e.g., "192.168.1.1").

        Returns:
            int: 32-bit integer representation.
        """
        parts = ipv4.split(".")
        if len(parts) != 4:
            raise ValueError(f"Invalid IPv4 address: {ipv4}")
        return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])

    @staticmethod
    def _int_to_ipv4(ip_int: int) -> str:
        """Convert 32-bit integer to IPv4 string.

        Args:
            ip_int: 32-bit integer representation.

        Returns:
            str: IPv4 address string.
        """
        return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"
