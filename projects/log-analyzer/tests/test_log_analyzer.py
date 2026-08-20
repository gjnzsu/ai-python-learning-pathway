import logging
import sys
from collections.abc import Iterator
from contextlib import (
    AbstractContextManager,
    nullcontext,
)
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from log_analyzer import (
    FileLogSource,
    LogEvent,
    count_log_levels,
    filter_events_by_level,
    filter_logs_by_level,
    main,
    open_log_lines,
    parse_log_line,
    parse_log_lines,
    print_matching_events,
    read_log_lines,
)
from log_analyzer.cli import (
    run,
)


def test_parses_a_valid_log_line() -> None:
    line = "2026-08-01T10:15:00|ERROR|database timeout"

    event = parse_log_line(line)

    assert event == LogEvent(
        timestamp="2026-08-01T10:15:00",
        level="ERROR",
        message="database timeout",
    )


def test_rejects_log_line_with_missing_fields() -> None:
    line = "2026-08-01T10:15:00|ERROR"

    with pytest.raises(
        ValueError,
        match="expected exactly 3 fields",
    ):
        parse_log_line(line)


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        pytest.param(
            [
                "2026-08-01T10:15:00|INFO|server started",
                "2026-08-01T10:16:00|ERROR|database timeout",
                "2026-08-01T10:17:00|INFO|request completed",
            ],
            {"INFO": 2, "ERROR": 1},
            id="repeated-level",
        ),
        pytest.param(
            [
                "2026-08-01T10:15:00|INFO|server started",
                "2026-08-01T10:16:00|ERROR|database timeout",
                "2026-08-01T10:17:00|WARN|request completed",
            ],
            {"INFO": 1, "ERROR": 1, "WARN": 1},
            id="previously-unseen-level",
        ),
        pytest.param(
            [],
            {},
            id="empty-input",
        ),
    ],
)
def test_counts_log_levels(
    lines: list[str],
    expected: dict[str, int],
) -> None:
    counts = count_log_levels(lines)

    assert counts == expected


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "app.log"
    file_path.write_text(
        "2026-08-08T10:00:00|INFO|server started\n"
        "2026-08-08T10:01:00|ERROR|database timeout\n",
        encoding="utf-8",
    )
    return file_path


def test_reads_multiple_lines_from_file(log_file: Path) -> None:
    lines = read_log_lines(str(log_file))

    assert lines == [
        "2026-08-08T10:00:00|INFO|server started",
        "2026-08-08T10:01:00|ERROR|database timeout",
    ]


def test_returns_empty_list_for_empty_file(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.log"
    file_path.write_text("", encoding="utf-8")

    lines = read_log_lines(str(file_path))

    assert lines == []


def test_raises_error_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "missing.log"

    with pytest.raises(FileNotFoundError):
        read_log_lines(str(file_path))


def test_prints_logs_matching_requested_level(
    log_file: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([str(log_file), "ERROR"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ("2026-08-08T10:01:00|ERROR|database timeout\n")
    assert captured.err == ""


def test_returns_usage_error_when_arguments_are_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "usage:" in captured.err
    assert "the following arguments are required" in captured.err


def test_compares_events_by_field_values() -> None:
    first_event = LogEvent(
        timestamp="2026-08-08T10:01:00",
        level="ERROR",
        message="database timeout",
    )

    second_event = LogEvent(
        timestamp="2026-08-08T10:01:00",
        level="ERROR",
        message="database timeout",
    )

    assert first_event == second_event


def test_parses_multiple_lines() -> None:
    lines = [
        "2026-08-08T10:00:00|INFO|server started",
        "2026-08-08T10:01:00|ERROR|database timeout",
    ]

    events = list(parse_log_lines(lines))

    assert events == [
        LogEvent(
            timestamp="2026-08-08T10:00:00",
            level="INFO",
            message="server started",
        ),
        LogEvent(
            timestamp="2026-08-08T10:01:00",
            level="ERROR",
            message="database timeout",
        ),
    ]


def test_parses_lines_lazily() -> None:
    lines = [
        "2026-08-08T10:00:00|INFO|server started",
        "invalid line",
    ]

    events = parse_log_lines(lines)

    first_event = next(events)

    assert first_event.level == "INFO"

    with pytest.raises(
        ValueError,
        match="expected exactly 3 fields",
    ):
        next(events)


def test_yields_matching_events() -> None:
    info_event = LogEvent(
        timestamp="2026-08-08T10:00:00",
        level="INFO",
        message="server started",
    )
    error_event = LogEvent(
        timestamp="2026-08-08T10:01:00",
        level="ERROR",
        message="database timeout",
    )

    events = filter_events_by_level(
        [info_event, error_event],
        "ERROR",
    )

    assert list(events) == [error_event]


def test_rejects_empty_target_level_immediately() -> None:
    with pytest.raises(
        ValueError,
        match="target level must not be empty",
    ):
        filter_events_by_level([], "")


def test_filters_logs_by_level() -> None:
    lines = [
        "2026-08-01T10:15:00|INFO|server started",
        "2026-08-01T10:16:00|ERROR|database timeout",
        "2026-08-01T10:17:00|INFO|request completed",
    ]

    events = filter_logs_by_level(lines, "ERROR")

    assert events == [
        LogEvent(
            timestamp="2026-08-01T10:16:00",
            level="ERROR",
            message="database timeout",
        )
    ]


def test_rejects_empty_target_level() -> None:
    lines: list[str] = []

    with pytest.raises(
        ValueError,
        match="target level must not be empty",
    ):
        filter_logs_by_level(lines, "")


def test_yields_stripped_lines_as_an_iterator(
    log_file: Path,
) -> None:
    with open_log_lines(str(log_file)) as lines:
        assert iter(lines) is lines
        first_line = next(lines)

    assert first_line == ("2026-08-08T10:00:00|INFO|server started")


def test_reads_multiple_lines_from_path_object(log_file: Path) -> None:
    lines = read_log_lines(log_file)

    assert lines == [
        "2026-08-08T10:00:00|INFO|server started",
        "2026-08-08T10:01:00|ERROR|database timeout",
    ]


def test_file_log_source_accepts_path(log_file: Path) -> None:
    source = FileLogSource(log_file)

    with source.open_lines() as lines:
        first = next(lines)

    assert first == "2026-08-08T10:00:00|INFO|server started"


def test_closes_file_when_context_exits() -> None:
    log_file = StringIO(
        "2026-08-08T10:00:00|INFO|server started\n"
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )

    with (
        patch("pathlib.Path.open", return_value=log_file),
        open_log_lines("app.log") as lines,
    ):
        next(lines)
        assert not log_file.closed

    assert log_file.closed


def test_closes_file_when_consumer_raises() -> None:
    log_file = StringIO("2026-08-08T10:00:00|INFO|server started\n" "invalid line\n")

    with (
        pytest.raises(
            ValueError,
            match="expected exactly 3 fields",
        ),
        patch("pathlib.Path.open", return_value=log_file),
        open_log_lines("app.log") as lines,
    ):
        events = parse_log_lines(lines)
        list(events)

    assert log_file.closed


@dataclass(frozen=True)
class MemoryLogSource:
    lines: tuple[str, ...]

    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        return nullcontext(iter(self.lines))


def test_prints_events_from_a_structural_log_source(
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = MemoryLogSource(
        lines=(
            "2026-08-08T10:00:00|INFO|server started",
            "2026-08-08T10:01:00|ERROR|database timeout",
        ),
    )

    print_matching_events(source, "ERROR")

    captured = capsys.readouterr()
    assert captured.out == ("2026-08-08T10:01:00|ERROR|database timeout\n")
    assert captured.err == ""

def test_returns_io_error_code_for_missing_log_file(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(tmp_path / "missing.log"), "ERROR"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "failed to read log file" in captured.err


def test_returns_usage_error_on_invalid_level(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["sample.log", "VERBOSE"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "invalid log level" in captured.err


def test_returns_io_error_code_for_permission_issue(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("log_analyzer.core.open_log_lines", side_effect=OSError("permission denied")):
        exit_code = main([str(tmp_path / "app.log"), "ERROR"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "failed to read log file" in captured.err


def test_invalid_level_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        main(["sample.log", "VERBOSE"])

    assert any(
        "invalid log level: VERBOSE" in record.message
        for record in caplog.records
    )


def test_io_error_is_logged(tmp_path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
         exit_code = main([str(tmp_path / "app.log"), "ERROR"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "failed to read log file" in captured.err
    assert any(
        record.levelname == "ERROR" and "failed to read log file" in record.message
        for record in caplog.records
    )


def test_returns_zero_for_help(capsys:pytest.CaptureFixture[str],) -> None:
    exit_code = main(["--help"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage:" in captured.out
    assert "log_file" in captured.out
    assert "level" in captured.out
    assert captured.err == ""


def test_run_uses_command_line_arguments(
    log_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["log-analyzer", str(log_file), "ERROR"])

    with pytest.raises(SystemExit) as error:
        run()

    captured = capsys.readouterr()

    assert error.value.code == 0
    assert captured.out == (
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )
