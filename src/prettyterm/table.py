from typing import Any

from rich.console import Console
from rich.table import Table


def print_table(data: dict[str, Any], title: str = "", show_lines: bool = False):
    """Print a dict as a table with keys as rows.

    Args:
        data: Dictionary to display as rows (key: value)
        title: Optional table title
        show_lines: Whether to show lines between rows
    """
    table = Table(title=title, show_lines=show_lines)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="#FFAC4D")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    Console().print(table)


# --- Usage Example ---

if __name__ == "__main__":
    data = {"Name": "Alice", "Age": 30, "City": "Wonderland"}
    print_table(data, title="Users")
