import logging
import sys
from typing import Final

from .core import FileLogSource, print_matching_events

LOGGER: Final = logging.getLogger(__name__)
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
INVALID_LEVEL_ERROR: Final = "invalid log level"
IO_ERROR_PREFIX: Final = "failed to read log file"


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        message = "usage: python log_analyzer.py <log-file> <level>"
        print(message, file=sys.stderr)
        LOGGER.error(message)
        return 2

    file_path, level = arguments
    level = level.upper()

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
