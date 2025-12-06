"""Unit tests for PGM protocol packet serialization."""

import pytest

from src.protocol import PacketType, PGMPacket, UserPayload


class TestPGMPacketSerialization:
    """Test PGM packet pack/unpack with network byte order."""

    def test_data_packet_roundtrip(self):
        """Test DATA packet serialization and deserialization."""
        payload = b"\x01\x02\x03\x04\x05"
        packet = PGMPacket(packet_type=PacketType.DATA, sequence=12345, payload=payload)

        # Pack and unpack
        packed = packet.pack()
        unpacked = PGMPacket.unpack(packed)

        assert unpacked.packet_type == PacketType.DATA
        assert unpacked.sequence == 12345
        assert unpacked.payload == payload

    def test_spm_packet_roundtrip(self):
        """Test SPM packet serialization and deserialization."""
        packet = PGMPacket(
            packet_type=PacketType.SPM, sequence=99999, last_hop_host="10.0.0.1", last_hop_port=8080
        )

        # Pack and unpack
        packed = packet.pack()
        unpacked = PGMPacket.unpack(packed)

        assert unpacked.packet_type == PacketType.SPM
        assert unpacked.sequence == 99999
        assert unpacked.last_hop_host == "10.0.0.1"
        assert unpacked.last_hop_port == 8080

    def test_nak_packet_roundtrip(self):
        """Test NAK packet serialization and deserialization."""
        packet = PGMPacket(packet_type=PacketType.NAK, sequence=0, requested_sequence=54321)

        # Pack and unpack
        packed = packet.pack()
        unpacked = PGMPacket.unpack(packed)

        assert unpacked.packet_type == PacketType.NAK
        assert unpacked.requested_sequence == 54321

    def test_ipv4_conversion(self):
        """Test IPv4 string to int conversion."""
        # Test various IP addresses
        test_cases = [
            ("0.0.0.0", 0),
            ("255.255.255.255", 0xFFFFFFFF),
            ("192.168.1.1", (192 << 24) | (168 << 16) | (1 << 8) | 1),
            ("10.0.0.1", (10 << 24) | 1),
        ]

        for ip_str, expected_int in test_cases:
            result = PGMPacket._ipv4_to_int(ip_str)
            assert result == expected_int, f"Failed for {ip_str}"

            # Test round trip
            back_to_str = PGMPacket._int_to_ipv4(result)
            assert back_to_str == ip_str, f"Round trip failed for {ip_str}"

    def test_network_byte_order(self):
        """Test that packet uses big endian (network byte order)."""
        packet = PGMPacket(packet_type=PacketType.DATA, sequence=0x12345678, payload=b"\x00")

        packed = packet.pack()

        # First byte should be packet type
        assert packed[0] == PacketType.DATA

        # Next 4 bytes should be sequence in big endian
        seq_bytes = packed[1:5]
        assert seq_bytes == b"\x12\x34\x56\x78"

    def test_data_packet_requires_payload(self):
        """Test that DATA packet requires payload."""
        packet = PGMPacket(packet_type=PacketType.DATA, sequence=1, payload=None)

        with pytest.raises(ValueError, match="DATA packet requires payload"):
            packet.pack()

    def test_spm_packet_requires_hop_info(self):
        """Test that SPM packet requires last hop information."""
        packet = PGMPacket(
            packet_type=PacketType.SPM, sequence=1, last_hop_host=None, last_hop_port=None
        )

        with pytest.raises(ValueError, match="SPM packet requires last_hop_host and last_hop_port"):
            packet.pack()

    def test_nak_packet_requires_requested_sequence(self):
        """Test that NAK packet requires requested sequence."""
        packet = PGMPacket(packet_type=PacketType.NAK, sequence=1, requested_sequence=None)

        with pytest.raises(ValueError, match="NAK packet requires requested_sequence"):
            packet.pack()

    def test_packet_too_short(self):
        """Test unpacking packet that is too short."""
        with pytest.raises(ValueError, match="Packet too short"):
            PGMPacket.unpack(b"\x00")

    def test_invalid_packet_type(self):
        """Test unpacking packet with invalid type."""
        # Create packet with invalid type (99)
        invalid_data = b"\x63\x00\x00\x00\x01"  # type=99, seq=1

        with pytest.raises(ValueError):
            PGMPacket.unpack(invalid_data)


class TestUserPayloadABC:
    """Test UserPayload abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that UserPayload cannot be instantiated directly."""
        with pytest.raises(TypeError):
            UserPayload()

    def test_concrete_implementation(self):
        """Test a concrete UserPayload implementation."""

        class IntPayload(UserPayload):
            def __init__(self, value: int = 0):
                self.value = value

            def pack(self) -> bytes:
                return self.value.to_bytes(4, byteorder="big", signed=True)

            def unpack(self, data: bytes) -> None:
                self.value = int.from_bytes(data[:4], byteorder="big", signed=True)

        # Test pack
        payload = IntPayload(42)
        packed = payload.pack()
        assert packed == b"\x00\x00\x00\x2a"

        # Test unpack
        payload2 = IntPayload()
        payload2.unpack(packed)
        assert payload2.value == 42


class TestPacketSizes:
    """Test packet sizes are as expected."""

    def test_data_packet_size(self):
        """Test DATA packet size calculation."""
        payload = b"\x00" * 100
        packet = PGMPacket(packet_type=PacketType.DATA, sequence=1, payload=payload)
        packed = packet.pack()

        # Common header (5 bytes) + payload (100 bytes)
        assert len(packed) == 5 + 100

    def test_spm_packet_size(self):
        """Test SPM packet size is fixed."""
        packet = PGMPacket(
            packet_type=PacketType.SPM, sequence=1, last_hop_host="192.168.1.1", last_hop_port=5000
        )
        packed = packet.pack()

        # Common header (5 bytes) + IPv4 (4 bytes) + port (2 bytes)
        assert len(packed) == 5 + 4 + 2

    def test_nak_packet_size(self):
        """Test NAK packet size is fixed."""
        packet = PGMPacket(packet_type=PacketType.NAK, sequence=0, requested_sequence=100)
        packed = packet.pack()

        # Common header (5 bytes) + requested_sequence (4 bytes)
        assert len(packed) == 5 + 4
