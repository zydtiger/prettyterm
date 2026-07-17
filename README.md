# [prettyterm](https://github.com/zydtiger/prettyterm)

Pretty terminal utilities wrapped around [Rich](https://rich.readthedocs.io/): colorful progress bars, dict-to-table printing, TTY-aware logging, and more.

## Installation

```bash
pip install prettyterm
```

## Features

### `track()` - tqdm-like Progress Bar

A clean, colorful progress bar wrapper around Rich's progress module. Drop-in replacement for tqdm with enhanced formatting.

**Features:**

- Progress bar with completion percentage
- Elapsed and remaining time
- Iteration speed (it/s)
- Dynamic postfix updates (string or dict)
- Auto-detects sequence length

```python
from prettyterm import track

# Basic usage
for i in track(range(100), desc="Processing"):
    # Your code here
    pass

# With dynamic postfix
pbar = track(range(100), desc="Epoch 3")
for i in pbar:
    pbar.set_postfix({"loss": f"{0.5}", "acc": f"{95}%"})
```

**Output:**

<img src="https://raw.githubusercontent.com/zydtiger/prettyterm/dev/examples/pbar.png" alt="Progress bar example">

---

### `print_table()` - Pretty Dictionary Tables

Display dictionaries as colorful, formatted tables. Great for configuration display, stats output, or debugging.

**Features:**

- Automatic column sizing
- Color-coded columns (cyan keys, orange values)
- Optional table title
- Optional row dividers

```python
from prettyterm import print_table

data = {
    "Name": "Alice",
    "Age": 30,
    "City": "Wonderland",
    "Role": "Developer"
}

print_table(data, title="User Info", show_lines=True)
```

**Output:**

<img src="https://raw.githubusercontent.com/zydtiger/prettyterm/dev/examples/table.png" alt="Table printing example">

---

### `setup_logging()` and `get_logger()` - Unified Logging with SUCCESS Level

Configure console and file logging explicitly, then get a standard logger with a custom `SUCCESS` level between `INFO` and `WARNING`. Importing `prettyterm` does not change the root logger.

**Features:**

- Automatic color only for an eligible interactive TTY
- Plain redirected console and UTF-8 file output with no ANSI escapes
- Console-only, file-only, or combined handlers
- Custom `SUCCESS` level (green on colored consoles and named `SUCCESS` in plain output)
- Idempotent reconfiguration without removing application-owned handlers
- Clean, piped format: `timestamp │ level │ name │ message`

```python
import logging

from prettyterm import get_logger, setup_logging

# Explicit setup; color="auto" is the default.
setup_logging(logging.INFO)

logger = get_logger("my_app")

logger.debug("Detailed debug info")
logger.info("Application started")
logger.success("Operation completed!")  # Custom level
logger.warning("Resource usage high")
logger.error("Connection failed")
logger.critical("System shutting down")
```

`color="auto"` enables console colors only when stderr is an interactive TTY. Redirected output, `NO_COLOR`, and `TERM=dumb` use the plain formatter. Use `color=True` or `color=False` for an explicit override.

**Output:**

<img src="https://raw.githubusercontent.com/zydtiger/prettyterm/dev/examples/logger.png" alt="Logger example">

**Log Colors:**

- `DEBUG` - Cyan
- `INFO` - White
- `SUCCESS` - Green (custom)
- `WARNING` - Yellow
- `ERROR` - Red
- `CRITICAL` - Red on white

**Console and file logging:**

File handlers are always UTF-8 and plain, even when the console is colored. `file_level=None` inherits `log_level`; set it explicitly when the file should capture more detail than the console.

```python
import logging

from prettyterm import get_logger, setup_logging

setup_logging(
    logging.INFO,
    log_file="app.log",
    file_level=logging.DEBUG,
)

logger = get_logger("my_app")
logger.debug("Written to app.log only")
logger.success("Visible as SUCCESS in the console and app.log")
```

**File-only logging:**

```python
from prettyterm import get_logger, setup_logging

setup_logging(console=False, log_file="worker.log")

logger = get_logger("worker")
logger.info("Running without a console handler")
logger.success("Written plainly as SUCCESS with no ANSI escapes")
```

Calling `setup_logging()` again closes and replaces only handlers previously installed by PrettyTerm. Handlers installed by the consuming application are preserved.

**Migrating to 0.3.0:**

Version 0.3.0 intentionally removes `setup_colored_logging()` and import-time root logger configuration. Applications must import `setup_logging` and call it explicitly before expecting PrettyTerm handlers. There is no compatibility alias.

## Development

```bash
# Install the project and locked development tools
uv sync --group dev

# Test, format-check, lint, type-check, and build
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv build

# Run examples
uv run python src/prettyterm/pbar.py
uv run python src/prettyterm/table.py
uv run python src/prettyterm/logger.py
```

## License

MIT
