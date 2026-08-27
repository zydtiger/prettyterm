# Repository Guidelines

PrettyTerm is a small pure-Python library of Rich-based terminal utilities: a
tqdm-style progress bar, a dict-to-table pretty-printer, and TTY-aware logging
setup with an extra `SUCCESS` level. It is a library only — there is no CLI
entry point.

## Project layout

- `src/prettyterm/__init__.py` — the entire public surface. `__all__` is
  `track`, `print_table`, `get_logger`, `setup_logging`. Importing the package
  must not touch the root logger; a test enforces this.
- `src/prettyterm/pbar.py` — `track()` and its iterator wrapper around
  `rich.progress.Progress`, including the `it/s` speed column and
  `set_postfix()`.
- `src/prettyterm/table.py` — `print_table()`, a two-column Rich table renderer
  for dicts.
- `src/prettyterm/logger.py` — `setup_logging()` and `get_logger()`. Owns the
  `SUCCESS` level (25), ANSI/control-sequence stripping for file output, the
  `color="auto"` TTY detection that honors `NO_COLOR` and `TERM=dumb`, and
  idempotent handler management that replaces only PrettyTerm-owned handlers.
- `tests/` — currently covers `logger.py` only. `pbar.py` and `table.py` have
  no tests; add them alongside any behavior change there.
- `Makefile` — release and publish plumbing (`build`, `clean`, `upload`) only.
  Development, testing, and linting go through `uv` and `prek`, not `make`.

## Tooling and validation

- Use `uv` for environment, dependency, and command operations. `.python-version`
  pins 3.12 as the development interpreter; the package supports 3.9 and later
  and CI exercises 3.9 through 3.14.
- Install the hook runner once per machine with `uv tool install prek`, then
  activate it in the clone with `prek install`. The config requires prek
  0.4.14 or later and installs three stages: `pre-commit`, `pre-push`, and
  `commit-msg`.
- Full: `prek run --all-files && prek run --all-files --hook-stage pre-push`
- Targeted: `uv run pytest tests/<file>` or a `::<test>` selector.
- Mechanical scope — lint, format, types, lockfile consistency, file hygiene —
  is defined solely by `.pre-commit-config.yaml`; tests run from the same file
  as a `pre-push` stage hook. Do not restate those commands or their scopes
  elsewhere.
- CI (`.github/workflows/ci.yml`) invokes the same hook runner rather than
  restating hook commands: a `lint` job runs the commit-stage hooks once, and a
  matrixed `test` job runs the pre-push stage on every supported Python
  version, then builds the package on the newest one.
- Whenever `pyproject.toml` dependency metadata changes, refresh `uv.lock` in
  the same change; the `uv-lock-check` hook fails otherwise.

## Documentation as tests

The fenced Python examples in the README's logging section are executed by
`tests/test_logger.py::test_readme_logging_examples_execute`. Editing that
section is a code change: keep the examples runnable or the suite fails.

## Git workflow

- Base branch: `dev`.
- Commit subjects are enforced by the `commit-msg` hook. A subject must start
  with `Merge ` or match `prefix: lowercase summary`, where prefix is one of
  `feat`, `fix`, `docs`, `test`, `build`, `ci`, `refactor`, `perf`, or `chore`,
  with an optional lowercase `(scope)`.
- Inspect status and diff before staging. Do not stage, commit, push, tag,
  release, or create forge objects unless the user requests that operation.

## Releases

- Follow Semantic Versioning, with `pyproject.toml` as the version source of
  truth. Record user-visible breaking changes in the README, which currently
  holds the migration notes in place of a changelog.
- Publishing runs through the `Makefile` targets and requires explicit approval
  immediately before the upload.
