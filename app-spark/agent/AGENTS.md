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

## Model tools

* The platform's own tools live in `app_spark_agent/tools/`, one module per tool, named after the tool the model sees. A tool's function name and docstring are what the model sees, and `settings.INSTRUCTIONS` names the tools: rename both together.

## User project dependencies

* Each workspace owns its `pyproject.toml` and `uv.lock`. The model creates them from `app-template/` with the `init_project` tool when it starts writing code; nothing is written at run start, so a chat-only turn leaves no commit. Every launch runs `uv sync` into `<workspace>/.venv`. See README "项目依赖".
* Changing the template's dependencies means editing `app-template/pyproject.toml`, running `make lock-app-template`, and updating the package list in `settings.INSTRUCTIONS`. `tests/test_project_env.py` enforces all three.

## Running tests

* All tests: `make test` (does not run `tests/e2e`)
* ALWAYS prefer specifying test files for efficiency
