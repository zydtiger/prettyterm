# prettyterm

Pretty terminal utilities wrapped around [Rich](https://rich.readthedocs.io/): colorful progress bars, dict-to-table printing, colored logging, and more.

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

<img src="./examples/pbar.png" alt="Progress bar example">

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

<img src="./examples/table.png" alt="Table printing example">

---

### `get_logger()` - Colored Logging with SUCCESS Level

Get a pre-configured logger with colored output and a custom `SUCCESS` logging level (sits between INFO and WARNING).

**Features:**

- Color-coded log levels
- Custom `SUCCESS` level (green)
- Auto-configured on import
- Clean, piped format: `timestamp │ level │ name │ message`

```python
from prettyterm import get_logger

logger = get_logger("my_app")

logger.debug("Detailed debug info")
logger.info("Application started")
logger.success("Operation completed!")  # Custom level
logger.warning("Resource usage high")
logger.error("Connection failed")
logger.critical("System shutting down")
```

**Output:**

<img src="./examples/logger.png" alt="Logger example">

**Log Colors:**

- `DEBUG` - Cyan
- `INFO` - White
- `SUCCESS` - Green (custom)
- `WARNING` - Yellow
- `ERROR` - Red
- `CRITICAL` - Red on white

**Custom Log Level:**

By default, logging is set to `INFO` level. You can change this by importing and calling `setup_colored_logging`:

```python
from prettyterm import get_logger, setup_colored_logging
import logging

# Set to DEBUG level to see all messages
setup_colored_logging(log_level=logging.DEBUG)

logger = get_logger("my_app")
logger.debug("This will now be visible")
```

## Development

```bash
# Install in editable mode
pip install -e .

# Run examples
python src/prettyterm/pbar.py
python src/prettyterm/table.py
python src/prettyterm/logger.py
```

## License

MIT
