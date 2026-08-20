import argparse
import logging
import sys
from dataclasses import dataclass
from typing import Final

from .core import FileLogSource, print_matching_events

LOGGER: Final = logging.getLogger(__name__)
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
INVALID_LEVEL_ERROR: Final = "invalid log level"
IO_ERROR_PREFIX: Final = "failed to read log file"


@dataclass(frozen=True)
class CliArguments:
    file_path: str
    level: str
    config_path: str | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="log-analyzer", description="Filter log events by level.")
    parser.add_argument("log_file", help="Path to the input log file.")
    parser.add_argument("level", help="Level to filter by.")
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Path to a TOML configuration file.",
    )
    return parser


def parse_arguments(arguments: list[str]) -> CliArguments:
    parser = build_parser()
    parsed = parser.parse_args(arguments)

    return CliArguments(
        file_path=parsed.log_file,
        level=parsed.level,
        config_path=parsed.config_path,
    )


def main(arguments: list[str]) -> int:
    try:
        cli_arguments = parse_arguments(arguments)
    except SystemExit as error:
        if error.code is None:
            return 0
        if isinstance(error.code, int):
            return error.code
        return 1

    file_path = cli_arguments.file_path
    level = cli_arguments.level.upper()

    if level not in VALID_LOG_LEVELS:
        message = f"{INVALID_LEVEL_ERROR}: {level}"
        print(message, file=sys.stderr)
        LOGGER.warning(message)
        return 2

    source = FileLogSource(file_path)
    try:
        print_matching_events(source, level)
    except OSError as error:
        message = f"{IO_ERROR_PREFIX}: {file_path}: {error}"
        print(message, file=sys.stderr)
        LOGGER.error(message)
        return 1
    return 0


def run() -> None:
    raise SystemExit(main(sys.argv[1:]))
