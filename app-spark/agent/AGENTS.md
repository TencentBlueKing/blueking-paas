## Context

You are in the app-spark agent component: the sandbox-side Agent process. It exposes `GET /health` and `POST /runs` (AG-UI over SSE), plus control-plane drain/context APIs, and runs as a single process in the cube sandbox.

## Common workflows

Use `make help` for available targets (they wrap `uv run`). Prefer a single test file, e.g. `uv run pytest tests/api/test_health.py`.

After editing Python files, run `uv run ruff format {filename}` and `uv run mypy {filename}`.

## Coding style

* For Python files, follow PEP-8.
* Do not introduce Django. HTTP is FastAPI.
* Python comments and docstrings are not rendered. Write identifiers as-is
  (`fake_model.py`); do not wrap them in RST/Markdown double backticks
  (``fake_model.py``).

## Spike vs formal work

* Containerization experiments and throwaway ideas go in **vibe-bkpaas**, not this repository.
* Formal work lands here: HTTP contract, toolchain, Dockerfile/tini entry, and later CFS / model / publish features tracked by AG-* stories.

## Running tests

* All tests: `make test` (does not run `tests/e2e`)
* ALWAYS prefer specifying test files for efficiency
