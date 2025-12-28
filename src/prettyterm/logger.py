import logging
from typing import Any, Protocol

import colorlog

# Add custom SUCCESS logging level
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


logging.Logger.success = success  # type: ignore


class LoggerProtocol(Protocol):
    """Protocol for logger with success method."""

    def debug(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def info(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def error(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def success(self, message: Any, *args: Any, **kwargs: Any) -> None: ...


def setup_colored_logging(log_level=logging.INFO):
    """
    Setup logging configuration with rich colors.

    Args:
        log_level: Logging level
        log_file: Optional log file path
    """
    # Create colored formatter for console
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s │ %(levelname)-8s │ %(name)-20.20s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        style="%",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "white",
            "SUCCESS": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> LoggerProtocol:
    """
    Get a logger with colored output configured.
    Uses the same handlers as configured in setup_colored_logging().

    Args:
        name: Logger name

    Returns:
        Logger instance with success method
    """
    logger = logging.getLogger(name)
    return logger  # type: ignore[return-value]
