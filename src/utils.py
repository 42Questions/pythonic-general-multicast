
def ipv4_to_int(ipv4: str) -> int:
    """Convert IPv4 string to 32-bit integer.

    Args:
        ipv4: IPv4 address string (e.g., "192.168.1.1")

    Returns:
        32-bit integer representation
    """
    parts = ipv4.split(".")
    if len(parts) != 4:
        raise ValueError(f"Invalid IPv4 address: {ipv4}")
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def int_to_ipv4(ip_int: int) -> str:
    """Convert 32-bit integer to IPv4 string.

    Args:
        ip_int: 32-bit integer representation

    Returns:
        IPv4 address string
    """
    return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"

