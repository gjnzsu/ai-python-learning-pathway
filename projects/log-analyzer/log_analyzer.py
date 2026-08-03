def parse_log_line(line: str) -> dict[str, str]:
    """Parse one log line into a structured event."""

    log_parts = line.split("|")

    if len(log_parts) != 3:
        raise ValueError("expected exactly 3 fields")

    timestamp, level, message = log_parts

    return {
        "timestamp": timestamp,
        "level": level,
        "message": message,
    }
