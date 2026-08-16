import sys

from .core import FileLogSource, print_matching_events


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(
            "usage: python log_analyzer.py <log-file> <level>",
            file=sys.stderr,
        )
        return 2

    file_path, level = arguments
    source = FileLogSource(file_path)
    print_matching_events(source, level)

    return 0


def run() -> None:
    raise SystemExit(main(sys.argv[1:]))