units = {
    'm': 60,
    'h': 3600,
    'd': 86400,
    'w': 604800,
}

def parse_interval(interval: str) -> int:
    unit = interval[-1]
    if unit not in units:
        raise ValueError(f"Invalid interval unit: {unit}")
    return int(interval[:-1]) * units[unit]