"""Security utilities for the drug discovery platform.

This module provides security-related functionality including
IP anonymization for privacy compliance.
"""

import hashlib
from typing import Optional


def anonymize_ip(ip_address: str) -> str:
    """Anonymize an IP address for logging purposes.
    
    This function anonymizes IP addresses to comply with privacy regulations
    while still allowing for basic analytics and abuse detection.
    
    For IPv4: Masks the last octet (e.g., 192.168.1.100 -> 192.168.1.0)
    For IPv6: Masks the last 80 bits (e.g., 2001:db8::1 -> 2001:db8::)
    
    Args:
        ip_address: The IP address to anonymize
    
    Returns:
        Anonymized IP address
    
    Validates: Requirement 12.8
    """
    if not ip_address:
        return "0.0.0.0"
    
    # Handle IPv4
    if "." in ip_address and ":" not in ip_address:
        parts = ip_address.split(".")
        if len(parts) == 4:
            # Mask last octet
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
    
    # Handle IPv6
    elif ":" in ip_address:
        # Simplified IPv6 anonymization - keep first 48 bits (3 groups)
        parts = ip_address.split(":")
        if len(parts) >= 3:
            # Keep first 3 groups, mask the rest
            return f"{parts[0]}:{parts[1]}:{parts[2]}::"
    
    # Fallback: return hashed version
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]


def get_client_ip(request) -> str:
    """Extract client IP address from request, handling proxies.
    
    Checks X-Forwarded-For and X-Real-IP headers for proxied requests.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (may contain multiple IPs)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (client IP)
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client
    if request.client:
        return request.client.host
    
    return "unknown"
