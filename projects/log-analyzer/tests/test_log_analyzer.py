import unittest

from log_analyzer import parse_log_line


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


if __name__ == "__main__":
    unittest.main()

