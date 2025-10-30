import re

# Example: Brand serials look like "BRD-2025-XXXXXX" where X are digits, last digit is Luhn-like check.
SERIAL_PATTERN = re.compile(r"^[A-Z]{3}-\d{4}-\d{6}$")

def luhn_like(num_str: str) -> int:
    # Simple Luhn-like checksum over digits only
    digits = [int(c) for c in num_str if c.isdigit()]
    s = 0
    dbl = False
    for d in reversed(digits):
        v = d*2 if dbl else d
        if v > 9: v -= 9
        s += v
        dbl = not dbl
    return s % 10

def validate_serial(serial: str):
    serial = serial.strip().upper()
    basic = bool(SERIAL_PATTERN.match(serial))
    checksum_ok = luhn_like(serial) == 0
    return {
        "normalized": serial,
        "format_ok": basic,
        "checksum_ok": checksum_ok,
        "valid": basic and checksum_ok
    }
