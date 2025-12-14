"""PGM protocol packet definitions and base classes."""

import struct
from enum import IntEnum
from dataclasses import dataclass
from src.packets.data import DataPacket
from src.packets.system import SystemPacket, SystemPacketTypes, SPM
SYSTEM_PACKET_CLASSES = {
    SystemPacketTypes.SPM: SPM,
}

class NetworkPacketTypes(IntEnum):
    SYSTEM = 0  # System Packet
    DATA = 1   # Data Packet

@dataclass
class NetworkPacket:
    payload: SystemPacket | DataPacket

    @property
    def packet_type(self) -> NetworkPacketTypes:
        """Derive packet type from payload."""
        if isinstance(self.payload, SystemPacket):
            return NetworkPacketTypes.SYSTEM
        else:
            return NetworkPacketTypes.DATA

    def pack(self) -> bytes:
        """Serialize NetworkPacket to bytes."""
        type_byte = struct.pack('!B', self.packet_type)
        return type_byte + self.payload.pack()

    @classmethod
    def from_bytes(cls, data: bytes) -> 'NetworkPacket':
        """Deserialize bytes into NetworkPacket.

        Simple two-level dispatch:
        1. Read network packet type (SYSTEM or DATA)
        2. For SYSTEM, use dispatch table to unpack concrete class
        """
        packet_type = NetworkPacketTypes(data[0])

        if packet_type == NetworkPacketTypes.SYSTEM:
            system_type = SystemPacketTypes(data[1])
            payload = SYSTEM_PACKET_CLASSES[system_type].unpack(data[1:])
        else:  # DATA
            payload = DataPacket.unpack(data[1:])

        return cls(payload=payload)
