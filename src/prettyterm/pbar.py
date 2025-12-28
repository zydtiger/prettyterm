from collections.abc import Iterable, Sized
from time import sleep
from typing import Any, cast

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text


class SpeedColumn(ProgressColumn):
    """Renders speed as 'it/s' and handles the 'None' case at startup."""

    def render(self, task):
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("? it/s", style="progress.data.speed")
        return Text(f"{speed:.2f} it/s", style="progress.data.speed")


class _TrackedIterator:
    """Iterator wrapper that allows updating postfix during iteration."""

    def __init__(self, sequence: Iterable, progress: Progress, task: TaskID):
        self._iterator = iter(sequence)
        self._progress = progress
        self._task = task

    def __iter__(self):
        return self

    def __next__(self):
        try:
            item = next(self._iterator)
            self._progress.update(self._task, advance=1)
            return item
        except StopIteration:
            self._progress.stop()
            raise

    def close(self):
        """Stop the progress display."""
        self._progress.stop()

    def set_postfix(self, postfix: str | dict[str, Any]):
        """Update the postfix text during iteration.

        Args:
            postfix: Either a string or dict[str, Any]. If dict, displays as "key: value • key: value"
        """
        if isinstance(postfix, dict):
            formatted = " • ".join(f"{k}: {v}" for k, v in postfix.items())
            self._progress.update(self._task, postfix=formatted)
        else:
            self._progress.update(self._task, postfix=postfix)


def track(
    sequence: Iterable,
    desc: str = "",
    total: int | None = None,
) -> _TrackedIterator:
    """
    A reusable tqdm-like wrapper for rich.progress.
    """
    # Attempt to get length if total isn't provided
    if total is None:
        try:
            total = len(cast(Sized, sequence))
        except TypeError:
            total = None

    columns = (
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("[dim]•"),
        TimeRemainingColumn(),
        SpeedColumn(),
        TextColumn("{task.fields[postfix]}"),
    )

    progress = Progress(*columns)
    progress.start()
    task = progress.add_task(desc, total=total, postfix="")

    return _TrackedIterator(sequence, progress, task)


# --- Usage Example ---

if __name__ == "__main__":
    # Now you can call it just like tqdm()
    pbar = track(range(100), desc="Epoch 3")
    for i in pbar:
        sleep(0.1)
        # String style
        # pbar.set_postfix(f"Loss: {100 - i}")
        # Dict style
        pbar.set_postfix({"loss": f"{100 - i}", "acc": f"{i}%"})
