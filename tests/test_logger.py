import io
import logging
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterator

import pytest

import prettyterm
from prettyterm import get_logger, setup_logging
from prettyterm.logger import SUCCESS_LEVEL

ANSI_ESCAPE = "\x1b["
HANDLER_OWNER_ATTRIBUTE = "_prettyterm_owned"


class ConsoleStream(io.StringIO):
    def __init__(self, is_tty: bool) -> None:
        super().__init__()
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def prettyterm_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, HANDLER_OWNER_ATTRIBUTE, False)
    ]


@pytest.fixture(autouse=True)
def restore_root_logger() -> Iterator[None]:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    yield

    for handler in list(root_logger.handlers):
        if handler not in original_handlers:
            root_logger.removeHandler(handler)
            handler.close()
    root_logger.setLevel(original_level)


def test_import_does_not_modify_root_logger() -> None:
    script = """
import logging

root = logging.getLogger()
handler = logging.StreamHandler()
root.handlers[:] = [handler]
root.setLevel(7)

import prettyterm

assert root.handlers == [handler]
assert root.level == 7
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_new_api_is_exported_and_old_api_is_absent() -> None:
    import prettyterm.logger as logger_module

    assert prettyterm.setup_logging is setup_logging
    assert "setup_logging" in prettyterm.__all__
    assert not hasattr(prettyterm, "setup_colored_logging")
    assert not hasattr(logger_module, "setup_colored_logging")


@pytest.mark.parametrize(
    ("is_tty", "expected_color"),
    [(True, True), (False, False)],
)
def test_auto_color_follows_console_tty(
    monkeypatch: pytest.MonkeyPatch, is_tty: bool, expected_color: bool
) -> None:
    stream = ConsoleStream(is_tty)
    monkeypatch.setattr(sys, "stderr", stream)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)

    setup_logging(color="auto")
    get_logger("tty-test").success("ready")

    assert (ANSI_ESCAPE in stream.getvalue()) is expected_color
    assert "SUCCESS" in stream.getvalue()


@pytest.mark.parametrize(
    ("environment", "value"),
    [("NO_COLOR", ""), ("TERM", "dumb"), ("TERM", "DUMB")],
)
def test_auto_color_honors_color_disabled_environment(
    monkeypatch: pytest.MonkeyPatch, environment: str, value: str
) -> None:
    stream = ConsoleStream(True)
    monkeypatch.setattr(sys, "stderr", stream)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.setenv(environment, value)

    setup_logging(color="auto")
    get_logger("environment-test").info("plain")

    assert ANSI_ESCAPE not in stream.getvalue()


def test_explicit_color_modes_override_auto_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disabled_stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", disabled_stream)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")

    setup_logging(color=True)
    get_logger("forced-color").info("colored")

    enabled_stream = ConsoleStream(True)
    monkeypatch.setattr(sys, "stderr", enabled_stream)
    setup_logging(color=False)
    get_logger("forced-plain").info("plain")

    assert ANSI_ESCAPE in disabled_stream.getvalue()
    assert ANSI_ESCAPE not in enabled_stream.getvalue()


def test_invalid_color_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="color must be"):
        setup_logging(color="sometimes")  # type: ignore[arg-type]


def test_console_only_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)

    setup_logging(console=True, color="auto")
    get_logger("console-only").info("console message")

    assert "INFO" in stream.getvalue()
    assert "console message" in stream.getvalue()
    assert not any(
        isinstance(handler, logging.FileHandler) for handler in prettyterm_handlers()
    )


def test_file_only_logging_is_utf8_plain_and_renders_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)
    log_path = tmp_path / "prettyterm.log"

    setup_logging(console=False, log_file=log_path)
    get_logger("file-only").success("完成 ✓")
    get_logger("file-only").info("\x1b[31mplain red\x1b[0m")

    contents = log_path.read_text(encoding="utf-8")
    assert stream.getvalue() == ""
    assert ANSI_ESCAPE not in contents
    assert "SUCCESS" in contents
    assert "完成 ✓" in contents
    assert "plain red" in contents


def test_file_only_setup_does_not_probe_console_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DetachedStream:
        def isatty(self) -> bool:
            raise AssertionError("file-only setup must not inspect stderr")

    monkeypatch.setattr(sys, "stderr", DetachedStream())
    log_path = tmp_path / "detached.log"

    setup_logging(console=False, log_file=log_path)
    get_logger("detached").success("file logging works")

    contents = log_path.read_text(encoding="utf-8")
    assert "SUCCESS" in contents
    assert "file logging works" in contents


def test_plain_handlers_strip_escape_sequences_without_losing_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)
    log_path = tmp_path / "plain.log"

    setup_logging(console=True, color=False, log_file=log_path)
    get_logger("plain-handlers").info("\x1bcreset")

    file_contents = log_path.read_text(encoding="utf-8")
    assert "\x1b" not in stream.getvalue()
    assert "\x1b" not in file_contents
    assert "reset" in stream.getvalue()
    assert "reset" in file_contents


def test_plain_handlers_strip_controls_and_preserve_text_after_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)
    log_path = tmp_path / "controls.log"

    setup_logging(console=True, color=False, log_file=log_path)
    get_logger("control-handlers").info(
        "before\x07\x08\r\x1b]title\x18after-osc-can"
        "\x1b]title\x1aafter-osc-sub"
        "\x1b[31\x18after-csi-can"
        "\x1b[31\x1aafter-csi-sub"
    )

    expected_text = "beforeafter-osc-canafter-osc-subafter-csi-canafter-csi-sub"
    file_contents = log_path.read_text(encoding="utf-8")
    assert expected_text in stream.getvalue()
    assert expected_text in file_contents
    for control in ("\x07", "\x08", "\r", "\x18", "\x1a", "\x1b"):
        assert control not in stream.getvalue()
        assert control not in file_contents


def test_file_level_none_inherits_nondefault_log_level(tmp_path: Path) -> None:
    log_path = tmp_path / "inherited-level.log"

    setup_logging(
        logging.WARNING,
        console=False,
        log_file=log_path,
        file_level=None,
    )
    logger = get_logger("inherited-level")
    logger.info("filtered detail")
    logger.warning("visible warning")

    contents = log_path.read_text(encoding="utf-8")
    assert "filtered detail" not in contents
    assert "visible warning" in contents
    file_handler = next(
        handler
        for handler in prettyterm_handlers()
        if isinstance(handler, logging.FileHandler)
    )
    assert file_handler.level == logging.WARNING


def test_combined_handlers_use_independent_levels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)
    log_path = tmp_path / "combined.log"

    setup_logging(
        logging.INFO,
        console=True,
        color=False,
        log_file=log_path,
        file_level=logging.DEBUG,
    )
    logger = get_logger("combined")
    logger.debug("file detail")
    logger.info("shared message")

    contents = log_path.read_text(encoding="utf-8")
    assert "file detail" not in stream.getvalue()
    assert "shared message" in stream.getvalue()
    assert "file detail" in contents
    assert "shared message" in contents
    assert ANSI_ESCAPE not in contents


def test_repeated_setup_replaces_and_closes_prettyterm_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", first_stream)
    first_path = tmp_path / "first.log"
    setup_logging(console=True, color=False, log_file=first_path)
    first_handlers = prettyterm_handlers()
    first_file_handler = next(
        handler
        for handler in first_handlers
        if isinstance(handler, logging.FileHandler)
    )

    second_stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", second_stream)
    second_path = tmp_path / "second.log"
    setup_logging(console=True, color=False, log_file=second_path)
    get_logger("replacement").info("once")

    root_handlers = prettyterm_handlers()
    assert len(root_handlers) == 2
    assert not any(handler in root_handlers for handler in first_handlers)
    assert first_file_handler.stream is None
    assert first_stream.getvalue() == ""
    assert second_stream.getvalue().count("once") == 1
    assert second_path.read_text(encoding="utf-8").count("once") == 1


def test_invalid_handlerless_reconfiguration_preserves_active_handlers(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "active.log"
    setup_logging(console=False, log_file=log_path)
    original_handlers = prettyterm_handlers()
    original_file_handler = next(
        handler
        for handler in original_handlers
        if isinstance(handler, logging.FileHandler)
    )

    with pytest.raises(ValueError, match="Unknown level"):
        setup_logging("NOT_A_LEVEL", console=False)

    assert prettyterm_handlers() == original_handlers
    assert original_file_handler.stream is not None
    get_logger("still-active").info("configuration preserved")
    assert "configuration preserved" in log_path.read_text(encoding="utf-8")


def test_handler_construction_failure_preserves_active_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)
    setup_logging(logging.WARNING, console=True, color=False)
    original_handlers = prettyterm_handlers()
    original_level = logging.getLogger().level

    with pytest.raises(FileNotFoundError):
        setup_logging(
            logging.DEBUG,
            console=True,
            color=False,
            log_file=tmp_path / "missing" / "failure.log",
        )

    assert prettyterm_handlers() == original_handlers
    assert logging.getLogger().level == original_level
    get_logger("construction-failure").warning("configuration preserved")
    assert "configuration preserved" in stream.getvalue()


def test_concurrent_setup_leaves_one_owned_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_logger = logging.getLogger()
    setup_logging(console=True, color=False)
    original_remove = root_logger.removeHandler

    def slow_remove(handler: logging.Handler) -> None:
        original_remove(handler)
        time.sleep(0.01)

    monkeypatch.setattr(root_logger, "removeHandler", slow_remove)
    start = threading.Barrier(4)
    errors = []

    def configure() -> None:
        try:
            start.wait()
            setup_logging(console=True, color=False)
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=configure) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(prettyterm_handlers()) == 1


def test_close_failure_keeps_replacement_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CloseFailureHandler(logging.Handler):
        def close(self) -> None:
            raise OSError("close failed")

    failing_handler = CloseFailureHandler()
    setattr(failing_handler, HANDLER_OWNER_ATTRIBUTE, True)
    logging.getLogger().addHandler(failing_handler)
    stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", stream)

    with pytest.raises(OSError, match="close failed"):
        setup_logging(console=True, color=False)

    assert failing_handler not in logging.getLogger().handlers
    assert len(prettyterm_handlers()) == 1
    get_logger("replacement-active").info("still logging")
    assert "still logging" in stream.getvalue()


def test_application_handlers_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    application_stream = io.StringIO()
    application_handler = logging.StreamHandler(application_stream)
    application_handler.setLevel(logging.ERROR)
    application_formatter = logging.Formatter("APP %(message)s")
    application_handler.setFormatter(application_formatter)
    logging.getLogger().addHandler(application_handler)

    console_stream = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", console_stream)
    setup_logging(color=False)
    setup_logging(color=False)
    get_logger("preservation").error("still here")

    assert application_handler in logging.getLogger().handlers
    assert application_handler.level == logging.ERROR
    assert application_handler.formatter is application_formatter
    assert application_stream.getvalue() == "APP still here\n"
    assert console_stream.getvalue().count("still here") == 1


def test_logger_retains_standard_and_success_methods() -> None:
    logger = get_logger("protocol")

    for method_name in (
        "debug",
        "info",
        "warning",
        "error",
        "exception",
        "critical",
        "success",
    ):
        assert callable(getattr(logger, method_name))
    assert SUCCESS_LEVEL == 25
    assert logging.getLevelName(SUCCESS_LEVEL) == "SUCCESS"


def test_readme_logging_examples_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme_path = Path(__file__).parents[1] / "README.md"
    logging_section = (
        readme_path.read_text(encoding="utf-8")
        .split("### `setup_logging()`", 1)[1]
        .split("## Development", 1)[0]
    )
    examples = re.findall(r"```python\n(.*?)```", logging_section, flags=re.DOTALL)
    assert len(examples) == 3

    console_output = ConsoleStream(False)
    monkeypatch.setattr(sys, "stderr", console_output)
    monkeypatch.chdir(tmp_path)
    for index, example in enumerate(examples, start=1):
        exec(compile(example, f"README logging example {index}", "exec"), {})

    app_contents = (tmp_path / "app.log").read_text(encoding="utf-8")
    worker_contents = (tmp_path / "worker.log").read_text(encoding="utf-8")
    assert "SUCCESS" in app_contents
    assert "SUCCESS" in worker_contents
    assert "\x1b" not in app_contents
    assert "\x1b" not in worker_contents
