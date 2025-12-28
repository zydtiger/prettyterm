from prettyterm.logger import get_logger, setup_colored_logging
from prettyterm.pbar import track
from prettyterm.table import print_table

# Automatically setup colored logging when this module is imported
setup_colored_logging()

__all__ = ["track", "print_table", "get_logger", "setup_colored_logging"]
