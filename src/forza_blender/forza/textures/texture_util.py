import re

def convert_texture_name_to_decimal(name: str) -> int:
    m = re.search(r'(-?)0x([0-9A-Fa-f_]+)', name)
    if not m:
        raise ValueError("No hex literal like 0x... found")
    sign = -1 if m.group(1) == '-' else 1
    digits = m.group(2).replace('_', '')
    return sign * int(digits, 16)