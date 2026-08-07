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


def count_log_levels(line_array: list[str]) -> dict[str, int]:

    log_level_count: dict[str, int] = {}

    for line in line_array:
        level = parse_log_line(line)["level"]
        log_level_count[level] = log_level_count.get(level, 0) + 1

    return log_level_count


def filter_logs_by_level(line_array: list[str], level: str) -> list[dict[str, str]]:
    if level == "":
        raise ValueError("target level must not be empty")

    result_list: list[dict[str, str]] = []

    for line in line_array:
        line_dict = parse_log_line(line)

        if line_dict["level"] == level:
            result_list.append(line_dict)

    return result_list
