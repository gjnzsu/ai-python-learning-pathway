import unittest

from log_analyzer import count_log_levels, filter_logs_by_level, parse_log_line


class ParseLogLineTest(unittest.TestCase):
    def test_parses_a_valid_log_line(self) -> None:
        line = "2026-08-01T10:15:00|ERROR|database timeout"

        event = parse_log_line(line)

        self.assertEqual(
            event,
            {
                "timestamp": "2026-08-01T10:15:00",
                "level": "ERROR",
                "message": "database timeout",
            },
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
                {
                    "timestamp": "2026-08-01T10:16:00",
                    "level": "ERROR",
                    "message": "database timeout",
                }
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


if __name__ == "__main__":
    unittest.main()
