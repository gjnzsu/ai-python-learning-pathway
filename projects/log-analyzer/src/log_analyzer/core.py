from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    level: str
    message: str


class LogSource(Protocol):
    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        ...


def parse_log_line(line: str) -> LogEvent:
    """Parse one log line into a structured event."""

    log_parts = line.split("|")

    if len(log_parts) != 3:
        raise ValueError("expected exactly 3 fields")

    timestamp, level, message = log_parts

    return LogEvent(
        timestamp=timestamp,
        level=level,
        message=message,
    )


def count_log_levels(line_array: list[str]) -> dict[str, int]:
    log_level_count: dict[str, int] = {}

    for line in line_array:
        level = parse_log_line(line).level
        log_level_count[level] = log_level_count.get(level, 0) + 1

    return log_level_count


def filter_logs_by_level(line_array: list[str], level: str) -> list[LogEvent]:
    if level == "":
        raise ValueError("target level must not be empty")

    events = parse_log_lines(line_array)

    matching_events = filter_events_by_level(events, level)

    return list(matching_events)


def read_log_lines(file_path: str) -> list[str]:
    with open_log_lines(file_path) as lines:
        return list(lines)


@contextmanager
def open_log_lines(file_path: str) -> Iterator[Iterator[str]]:
    with open(file_path, "r", encoding="utf-8") as log_file:

        def stripped_lines() -> Iterator[str]:
            for line in log_file:
                yield line.rstrip("\r\n")

        yield stripped_lines()


@dataclass(frozen=True)
class FileLogSource:
    file_path: str

    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        return open_log_lines(self.file_path)


def parse_log_lines(lines: Iterable[str]) -> Iterator[LogEvent]:
    for line in lines:
        yield parse_log_line(line)


def filter_events_by_level(
    events: Iterable[LogEvent], level: str
) -> Iterator[LogEvent]:
    if level == "":
        raise ValueError("target level must not be empty")

    def matching_events() -> Iterator[LogEvent]:
        for event in events:
            if event.level == level:
                yield event

    return matching_events()


def print_matching_events(source: LogSource, level: str) -> None:
    with source.open_lines() as lines:
        events = parse_log_lines(lines)
        matching_events = filter_events_by_level(events, level)

        for event in matching_events:
            print(f"{event.timestamp}|{event.level}|{event.message}")
