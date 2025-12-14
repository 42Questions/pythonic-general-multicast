import struct
from typing import ClassVar

from pydantic import BaseModel, Field, computed_field


class DataPacket(BaseModel):
    """Data packet containing payload bytes.

    Attributes:
        data: Actual data payload
        size: Size of data in bytes (computed property)
    """

    model_config = {"frozen": True}

    SIZE_FORMAT: ClassVar[str] = "!I"

    data: bytes = Field(..., min_length=1, description="Actual data payload")

    @computed_field
    def size(self) -> int:
        """Size of data in bytes."""
        return len(self.data)

    def pack(self) -> bytes:
        """Serialize DataPacket to bytes."""
        return struct.pack(self.SIZE_FORMAT, self.size) + self.data

    @classmethod
    def unpack(cls, data: bytes) -> DataPacket:
        """Deserialize bytes into DataPacket."""
        payload_data = data[struct.calcsize(cls.SIZE_FORMAT) :]
        return cls(data=payload_data)
