## Context

You are in the ap-spark repo, helping implement features, fix bugs, and refactor existing code.

## Common workflows

## Coding style

* For Python files, follow PEP-8.
* After editing Python files, run:
    - formatting: `uv run ruff format {filename}`
    - type-checking: `uv run mypy {filename}`

### Running tests

* Run all tests: `uv run pytest --reuse-db -s --maxfail=1 tests/`
* ALWAYS prefer specifying test files for efficiency