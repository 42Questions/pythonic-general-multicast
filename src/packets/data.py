import struct
from dataclasses import dataclass


@dataclass
class DataPacket:
    size: int  # Size of data in bytes
    data: bytes  # Actual data payload

    SIZE_FORMAT = "!I"
    SIZE_BYTES = struct.calcsize(SIZE_FORMAT)

    def pack(self) -> bytes:
        """Serialize DataPacket to bytes."""
        return struct.pack(self.SIZE_FORMAT, self.size) + self.data

    @classmethod
    def unpack(cls, data: bytes) -> DataPacket:
        """Deserialize bytes into DataPacket."""
        size = struct.unpack(cls.SIZE_FORMAT, data[: cls.SIZE_BYTES])[0]
        payload_data = data[cls.SIZE_BYTES :]
        return cls(size=size, data=payload_data)
