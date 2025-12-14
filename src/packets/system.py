"""PGM protocol packet definitions and base classes."""

import struct
from dataclasses import dataclass, field, fields
from enum import IntEnum
from typing import Self

from src.utils import int_to_ipv4, ipv4_to_int


class SystemPacketTypes(IntEnum):
    SPM = 0  # Source Path Message


@dataclass
class SystemPacket:
    packet_type: SystemPacketTypes = field(init=False, metadata={"format": "B"})

    def __post_init__(self) -> None:
        """Prevent direct instantiation of abstract base class."""
        if self.__class__ is SystemPacket:
            raise TypeError("Cannot instantiate abstract class SystemPacket directly")

    @classmethod
    def get_format(cls) -> str:
        """Generate struct format string from field metadata.

        Returns:
            str: Format string with network byte order prefix (e.g., '!BI')
        """
        format_chars = "".join(f.metadata["format"] for f in fields(cls))
        return f"!{format_chars}"

    @classmethod
    def get_size(cls) -> int:
        """Get the size of the packed header in bytes.

        Returns:
            int: Size in bytes
        """
        return struct.calcsize(cls.get_format())

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        """Deserialize bytes into packet instance."""
        values = struct.unpack(cls.get_format(), data[: cls.get_size()])
        # Map unpacked values to non-init fields
        field_names = [f.name for f in fields(cls) if f.init]
        return cls(**dict(zip(field_names, values[1:], strict=True)))  # Skip packet_type

    def pack(self) -> bytes:
        """Serialize packet to bytes."""
        values = [getattr(self, f.name) for f in fields(self.__class__)]
        return struct.pack(self.get_format(), *values)


@dataclass
class SPM(SystemPacket):
    packet_type: SystemPacketTypes = field(
        default=SystemPacketTypes.SPM, init=False, metadata={"format": "B"}
    )
    last_hop_host: int = field(metadata={"format": "I"})  # IPv4 address as uint32
    last_hop_port: int = field(metadata={"format": "H"})  # Port as uint16

    @classmethod
    def from_address(cls, host: str, port: int) -> SPM:
        """Create SPM from IPv4 address string and port.

        Args:
            host: IPv4 address string (e.g., "192.168.1.1")
            port: Port number (0-65535)

        Returns:
            SPM instance
        """
        host_int = ipv4_to_int(host)
        return cls(last_hop_host=host_int, last_hop_port=port)

    def __repr__(self) -> str:
        """Human-readable representation with IPv4 address and port."""
        host_str = int_to_ipv4(self.last_hop_host)
        return f"SPM(host='{host_str}', port={self.last_hop_port})"
