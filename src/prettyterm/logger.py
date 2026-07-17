import logging
import os
import sys
import threading
from typing import Any, Literal, Optional, Protocol, Union

import colorlog

SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

ColorMode = Union[Literal["auto"], bool]
LogFile = Union[str, os.PathLike[str]]

_LOG_FORMAT = "%(asctime)s │ %(levelname)-8s │ %(name)-20.20s │ %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_HANDLER_OWNER_ATTRIBUTE = "_prettyterm_owned"
_SETUP_LOCK = threading.RLock()


def _consume_csi(value: str, start: int) -> int:
    index = start
    while index < len(value):
        codepoint = ord(value[index])
        index += 1
        if codepoint in (0x18, 0x1A):
            break
        if 0x40 <= codepoint <= 0x7E:
            break
    return index


def _consume_control_string(value: str, start: int, *, bell_ends: bool) -> int:
    index = start
    while index < len(value):
        if bell_ends and value[index] == "\x07":
            return index + 1
        if value[index] == "\x9c":
            return index + 1
        if value[index] in "\x18\x1a":
            return index + 1
        if value[index] == "\x1b" and value[index + 1 : index + 2] == "\\":
            return index + 2
        index += 1
    return index


def _strip_ansi(value: str) -> str:
    """Remove ECMA-48 escape sequences and C1 controls from text."""
    plain = []
    index = 0

    while index < len(value):
        character = value[index]
        codepoint = ord(character)

        if character == "\x1b":
            marker = value[index + 1 : index + 2]
            if marker == "[":
                index = _consume_csi(value, index + 2)
            elif marker == "]":
                index = _consume_control_string(value, index + 2, bell_ends=True)
            elif marker and marker in "PX^_":
                index = _consume_control_string(value, index + 2, bell_ends=False)
            else:
                index += 1
                while index < len(value) and 0x20 <= ord(value[index]) <= 0x2F:
                    index += 1
                if index < len(value) and 0x30 <= ord(value[index]) <= 0x7E:
                    index += 1
        elif character == "\x9b":
            index = _consume_csi(value, index + 1)
        elif character in "\x90\x98\x9d\x9e\x9f":
            index = _consume_control_string(
                value,
                index + 1,
                bell_ends=character == "\x9d",
            )
        elif (
            codepoint < 0x20 and character not in "\t\n"
        ) or 0x7F <= codepoint <= 0x9F:
            index += 1
        else:
            plain.append(character)
            index += 1

    return "".join(plain)


def success(self: logging.Logger, message: Any, *args: Any, **kwargs: Any) -> None:
    """Log *message* at PrettyTerm's SUCCESS level."""
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


logging.Logger.success = success  # type: ignore[attr-defined]


class LoggerProtocol(Protocol):
    """Protocol for standard logger methods plus the custom success method."""

    def debug(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def info(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def error(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, message: Any, *args: Any, **kwargs: Any) -> None: ...
    def success(self, message: Any, *args: Any, **kwargs: Any) -> None: ...


class _PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return _strip_ansi(formatted)


class _ColoredFormatter(colorlog.ColoredFormatter):
    """Force color after PrettyTerm has applied its own eligibility policy."""

    def _blank_escape_codes(self) -> bool:
        return False

    def _colorize(self) -> bool:
        return True


def _plain_formatter() -> logging.Formatter:
    return _PlainFormatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)


def _colored_formatter() -> colorlog.ColoredFormatter:
    return _ColoredFormatter(
        f"%(log_color)s{_LOG_FORMAT}",
        datefmt=_DATE_FORMAT,
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


def _color_enabled(stream: Any, color: ColorMode) -> bool:
    if color is True:
        return True
    if color is False:
        return False
    if color != "auto":
        raise ValueError("color must be 'auto', True, or False")
    if "NO_COLOR" in os.environ or os.environ.get("TERM", "").lower() == "dumb":
        return False

    try:
        return bool(stream.isatty())
    except (AttributeError, OSError):
        return False


def _mark_owned(handler: logging.Handler) -> logging.Handler:
    setattr(handler, _HANDLER_OWNER_ATTRIBUTE, True)
    return handler


def _validated_level(level: Union[int, str]) -> int:
    validator = logging.NullHandler()
    validator.setLevel(level)
    return validator.level


def setup_logging(
    log_level: Union[int, str] = logging.INFO,
    *,
    console: bool = True,
    color: ColorMode = "auto",
    log_file: Optional[LogFile] = None,
    file_level: Optional[Union[int, str]] = None,
) -> None:
    """Configure PrettyTerm-owned console and file handlers on the root logger.

    Existing handlers installed by the application are preserved. Calling this
    function again safely replaces and closes handlers from an earlier call.
    Console color defaults to automatic TTY detection; file output is always
    UTF-8 text without ANSI color escapes.
    """
    with _SETUP_LOCK:
        _setup_logging(log_level, console, color, log_file, file_level)


def _setup_logging(
    log_level: Union[int, str],
    console: bool,
    color: ColorMode,
    log_file: Optional[LogFile],
    file_level: Optional[Union[int, str]],
) -> None:
    validated_log_level = _validated_level(log_level)
    validated_file_level = (
        validated_log_level if file_level is None else _validated_level(file_level)
    )
    new_handlers: list[logging.Handler] = []

    try:
        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(validated_log_level)
            formatter = (
                _colored_formatter()
                if _color_enabled(console_handler.stream, color)
                else _plain_formatter()
            )
            console_handler.setFormatter(formatter)
            new_handlers.append(_mark_owned(console_handler))
        else:
            # Validate the color mode even when no console handler is requested.
            _color_enabled(sys.stderr, color)

        if log_file is not None:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(validated_file_level)
            file_handler.setFormatter(_plain_formatter())
            new_handlers.append(_mark_owned(file_handler))
    except Exception:
        for handler in new_handlers:
            try:
                handler.close()
            except Exception:
                pass
        raise

    root_logger = logging.getLogger()
    owned_handlers = [
        handler
        for handler in root_logger.handlers
        if getattr(handler, _HANDLER_OWNER_ATTRIBUTE, False)
    ]

    previous_level = root_logger.level
    installed_handlers = []

    try:
        for handler in owned_handlers:
            root_logger.removeHandler(handler)

        if new_handlers:
            root_logger.setLevel(min(handler.level for handler in new_handlers))
        else:
            root_logger.setLevel(validated_log_level)

        for handler in new_handlers:
            root_logger.addHandler(handler)
            installed_handlers.append(handler)
    except Exception:
        for handler in installed_handlers:
            root_logger.removeHandler(handler)
        root_logger.setLevel(previous_level)
        for handler in owned_handlers:
            root_logger.addHandler(handler)
        for handler in new_handlers:
            try:
                handler.close()
            except Exception:
                pass
        raise

    close_error: Optional[Exception] = None
    for handler in owned_handlers:
        try:
            handler.close()
        except Exception as error:
            if close_error is None:
                close_error = error
    if close_error is not None:
        raise close_error


def get_logger(name: str) -> LoggerProtocol:
    """Return a standard logger supporting PrettyTerm's ``success()`` method."""
    logger = logging.getLogger(name)
    return logger  # type: ignore[return-value]


if __name__ == "__main__":
    setup_logging()
    logger = get_logger("demo")
    logger.debug("Debugging information")
    logger.info("Application started")
    logger.success("Operation completed successfully!")
    logger.warning("This is a warning")
    logger.error("An error occurred")
    logger.critical("Critical system failure")
