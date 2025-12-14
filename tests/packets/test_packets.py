"""Unit tests for PGM protocol packet serialization."""

import struct

import pytest

from src.packets.data import DataPacket
from src.packets.network import NetworkPacket, NetworkPacketTypes
from src.packets.system import SPM, SystemPacketTypes
from src.utils import int_to_ipv4, ipv4_to_int


class TestDataPacket:
    """Test DataPacket serialization."""

    def test_data_packet_roundtrip(self):
        """Test DATA packet serialization and deserialization."""
        payload_data = b"\x01\x02\x03\x04\x05"
        packet = DataPacket(size=len(payload_data), data=payload_data)

        # Pack and unpack
        packed = packet.pack()
        unpacked = DataPacket.unpack(packed)

        assert unpacked.size == len(payload_data)
        assert unpacked.data == payload_data

    def test_data_packet_size(self):
        """Test DATA packet size calculation."""
        payload_data = b"\x00" * 100
        packet = DataPacket(size=len(payload_data), data=payload_data)
        packed = packet.pack()

        # Size field (4 bytes) + payload (100 bytes)
        assert len(packed) == 4 + 100


class TestSystemPacket:
    """Test SystemPacket (SPM) serialization."""

    def test_spm_packet_roundtrip(self):
        """Test SPM packet serialization and deserialization."""
        host = "10.0.0.1"
        port = 8080
        packet = SPM.from_address(host, port)

        # Pack and unpack
        packed = packet.pack()
        unpacked = SPM.unpack(packed)

        assert unpacked.packet_type == SystemPacketTypes.SPM
        assert int_to_ipv4(unpacked.last_hop_host) == host
        assert unpacked.last_hop_port == port

    def test_spm_packet_repr(self):
        """Test SPM packet string representation."""
        packet = SPM.from_address("192.168.1.1", 5000)
        repr_str = repr(packet)

        assert "192.168.1.1" in repr_str
        assert "5000" in repr_str

    def test_spm_packet_size(self):
        """Test SPM packet size is fixed."""
        packet = SPM.from_address("192.168.1.1", 5000)
        packed = packet.pack()

        # packet_type (1 byte) + IPv4 (4 bytes) + port (2 bytes)
        assert len(packed) == 1 + 4 + 2


class TestNetworkPacket:
    """Test NetworkPacket two-level serialization."""

    def test_network_packet_with_data(self):
        """Test NetworkPacket containing DataPacket."""
        payload_data = b"\x01\x02\x03\x04\x05"
        data_packet = DataPacket(size=len(payload_data), data=payload_data)
        network_packet = NetworkPacket(payload=data_packet)

        # Check packet type
        assert network_packet.packet_type == NetworkPacketTypes.DATA

        # Pack and unpack
        packed = network_packet.pack()
        unpacked = NetworkPacket.from_bytes(packed)

        assert isinstance(unpacked.payload, DataPacket)
        assert unpacked.payload.data == payload_data

    def test_network_packet_with_system(self):
        """Test NetworkPacket containing SystemPacket (SPM)."""
        spm = SPM.from_address("10.0.0.1", 8080)
        network_packet = NetworkPacket(payload=spm)

        # Check packet type
        assert network_packet.packet_type == NetworkPacketTypes.SYSTEM

        # Pack and unpack
        packed = network_packet.pack()
        unpacked = NetworkPacket.from_bytes(packed)

        assert isinstance(unpacked.payload, SPM)
        assert int_to_ipv4(unpacked.payload.last_hop_host) == "10.0.0.1"
        assert unpacked.payload.last_hop_port == 8080


class TestIPv4Conversion:
    """Test IPv4 utility functions."""

    def test_ipv4_conversion(self):
        """Test IPv4 string to int conversion."""
        test_cases = [
            ("0.0.0.0", 0),
            ("255.255.255.255", 0xFFFFFFFF),
            ("192.168.1.1", (192 << 24) | (168 << 16) | (1 << 8) | 1),
            ("10.0.0.1", (10 << 24) | 1),
        ]

        for ip_str, expected_int in test_cases:
            result = ipv4_to_int(ip_str)
            assert result == expected_int, f"Failed for {ip_str}"

            # Test round trip
            back_to_str = int_to_ipv4(result)
            assert back_to_str == ip_str, f"Round trip failed for {ip_str}"


class TestNetworkByteOrder:
    """Test that packets use big endian (network byte order)."""

    def test_data_packet_byte_order(self):
        """Test that DataPacket size field uses network byte order."""
        payload_data = b"\x00"
        packet = DataPacket(size=0x12345678, data=payload_data)
        packed = packet.pack()

        # First 4 bytes should be size in big endian
        size_bytes = packed[:4]
        assert size_bytes == b"\x12\x34\x56\x78"

    def test_spm_packet_byte_order(self):
        """Test that SPM packet fields use network byte order."""
        packet = SPM.from_address("1.2.3.4", 0x1234)
        packed = packet.pack()

        # First byte should be packet type
        assert packed[0] == SystemPacketTypes.SPM

        # Next 4 bytes should be IP address in big endian
        ip_bytes = packed[1:5]
        assert ip_bytes == b"\x01\x02\x03\x04"

        # Next 2 bytes should be port in big endian
        port_bytes = packed[5:7]
        assert port_bytes == b"\x12\x34"


class TestPacketValidation:
    """Test packet validation and error handling."""

    def test_invalid_network_packet_type(self):
        """Test unpacking NetworkPacket with invalid type."""
        # Create packet with invalid type (99)
        invalid_data = b"\x63\x00\x00\x00\x01"

        with pytest.raises(ValueError):
            NetworkPacket.from_bytes(invalid_data)

    def test_data_packet_too_short(self):
        """Test unpacking DataPacket that is too short."""
        # Only 2 bytes, but need at least 4 for size field
        with pytest.raises(struct.error):
            DataPacket.unpack(b"\x00\x00")
