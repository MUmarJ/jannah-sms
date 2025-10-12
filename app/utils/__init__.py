"""Utility functions for common operations."""

import re


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to digits only.

    Args:
        phone: Phone number string (with or without formatting)

    Returns:
        str: Phone number with only digits
    """
    return re.sub(r"[^0-9]", "", phone)


def format_phone(phone: str) -> str:
    """
    Format phone number for display.

    Args:
        phone: Phone number string

    Returns:
        str: Formatted phone number (XXX) XXX-XXXX or +1 (XXX) XXX-XXXX
    """
    if not phone:
        return ""

    cleaned = normalize_phone(phone)

    if len(cleaned) == 10:
        return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    elif len(cleaned) == 11 and cleaned[0] == "1":
        return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"

    return phone
