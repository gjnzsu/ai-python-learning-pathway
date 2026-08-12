import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from log_analyzer import (
    count_log_levels,
    filter_logs_by_level,
    parse_log_line,
    read_log_lines,
    main,
    LogEvent,
    parse_log_lines,
    filter_events_by_level,
)


class ParseLogLineTest(unittest.TestCase):
    def test_parses_a_valid_log_line(self) -> None:
        line = "2026-08-01T10:15:00|ERROR|database timeout"

        event = parse_log_line(line)

        self.assertEqual(
            event,
            LogEvent(
                timestamp="2026-08-01T10:15:00",
                level="ERROR",
                message="database timeout",
            ),
        )

    def test_rejects_log_line_with_missing_fields(self) -> None:
        line = "2026-08-01T10:15:00|ERROR"

        with self.assertRaisesRegex(
            ValueError,
            "expected exactly 3 fields",
        ):
            parse_log_line(line)


class FilterLogsByLevelTest(unittest.TestCase):
    def test_filter_log_by_level(self) -> None:
        lines = [
            "2026-08-01T10:15:00|INFO|server started",
            "2026-08-01T10:16:00|ERROR|database timeout",
            "2026-08-01T10:17:00|INFO|request completed",
        ]

        events = filter_logs_by_level(lines, "ERROR")

        self.assertEqual(
            events,
            [
                LogEvent(
                    timestamp="2026-08-01T10:16:00",
                    level="ERROR",
                    message="database timeout",
                )
            ],
        )

    def test_rejects_empty_target_level(self) -> None:
        lines = []

        with self.assertRaisesRegex(
            ValueError,
            "target level must not be empty",
        ):
            filter_logs_by_level(lines, "")


class CountLogLevelsTest(unittest.TestCase):
    def test_counts_each_log_level(self) -> None:
        lines = [
            "2026-08-01T10:15:00|INFO|server started",
            "2026-08-01T10:16:00|ERROR|database timeout",
            "2026-08-01T10:17:00|INFO|request completed",
        ]

        counts = count_log_levels(lines)

        self.assertEqual(
            counts,
            {
                "INFO": 2,
                "ERROR": 1,
            },
        )

    def test_counts_a_previously_unseen_level(self) -> None:
        lines = [
            "2026-08-01T10:15:00|INFO|server started",
            "2026-08-01T10:16:00|ERROR|database timeout",
            "2026-08-01T10:17:00|WARN|request completed",
        ]

        counts = count_log_levels(lines)

        self.assertEqual(
            counts,
            {
                "INFO": 1,
                "ERROR": 1,
                "WARN": 1,
            }
        )

    def test_return_empty_dict(self) -> None:
        lines = []

        counts = count_log_levels(lines)

        self.assertEqual(
            counts,
            {

            }
        )
class ReadLogLineTest(unittest.TestCase):
    def test_reads_multiple_lines_from_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir)/"app.log"
            file_path.write_text(
                "2026-08-08T10:00:00|INFO|server started\n"
                "2026-08-08T10:01:00|ERROR|database timeout\n",
                encoding="utf-8",
            )

            lines = read_log_lines(str(file_path))

            self.assertEqual(
                lines,
                [
                    "2026-08-08T10:00:00|INFO|server started",
                    "2026-08-08T10:01:00|ERROR|database timeout",
                ],
            )

    def test_returns_empty_list_for_empty_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir)/"empty.log"
            file_path.write_text("", encoding="utf-8",)
            lines = read_log_lines(str(file_path))

        self.assertEqual(
            lines,
            [],
        )

    def test_raises_error_when_file_not_exist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir)/"missing.log"

            with self.assertRaises(FileNotFoundError):
                read_log_lines(str(file_path))

class MainTest(unittest.TestCase):
    def test_prints_logs_matching_requested_level(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "app.log"
            file_path.write_text(
                "2026-08-08T10:00:00|INFO|server started\n"
                "2026-08-08T10:01:00|ERROR|database timeout\n",
                encoding="utf-8",
            )
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main([str(file_path), "ERROR"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            output.getvalue(),
            "2026-08-08T10:01:00|ERROR|database timeout\n",
        )

    def test_returns_usage_error_when_arguments_are_missing(self) -> None:
        error_output = StringIO()

        with redirect_stderr(error_output):
            exit_code = main([])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            error_output.getvalue(),
            "usage: python log_analyzer.py <log-file> <level>\n",
    )

class LogEventTest(unittest.TestCase):
    def test_compares_events_by_field_values(self) -> None:
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

        self.assertEqual(first_event, second_event)

class ParseLogLinesTest(unittest.TestCase):
    def test_parses_multiple_lines(self) -> None:
        lines = [
            "2026-08-08T10:00:00|INFO|server started",
            "2026-08-08T10:01:00|ERROR|database timeout",
        ]

        events = list(parse_log_lines(lines))

        self.assertEqual(
            events,
            [
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
            ],
        )

    def test_parses_lines_lazily(self) -> None:
        lines = [
            "2026-08-08T10:00:00|INFO|server started",
            "invalid line",
        ]

        events = parse_log_lines(lines)

        first_event = next(events)

        self.assertEqual(first_event.level, "INFO")

        with self.assertRaisesRegex(
            ValueError,
            "expected exactly 3 fields",
        ):
            next(events)

class FilterEventsByLevelTest(unittest.TestCase):
    def test_yields_matching_events(self) -> None:
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

        self.assertEqual(list(events), [error_event])

    def test_rejects_empty_target_level_immediately(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "target level must not be empty",
        ):
            filter_events_by_level([], "")

if __name__ == "__main__":
    unittest.main()
