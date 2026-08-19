## Context

You are in the ap-spark repo, helping implement features, fix bugs, and refactor existing code.

## Common workflows

## Coding style

* For Python files, follow PEP-8.
* After editing Python files, run:
    - formatting: `uv run ruff format {filename}`
    - type-checking: `uv run mypy {filename}`
* Add Sphinx-style doc to public Python APIs. Include a short usage example for APIs whose invocation is not obvious.

### Design conventions

* Prefer frozen attrs classes for internal configuration and data models, and use cattrs to structure and validate untyped input.
    - Translate library validation failures into domain-level exceptions at module boundaries.
* Avoid Django `choices` when defining models if the choices might change in the future, document the supported values instead.


### Running tests

* Run all tests: `uv run pytest --reuse-db -s --maxfail=1 tests/`
* ALWAYS prefer specifying test files for efficiency