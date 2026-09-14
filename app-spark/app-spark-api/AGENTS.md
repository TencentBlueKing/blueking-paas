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
* Put pure queries on the model's manager/queryset, not in services; services orchestrate (transactions, translating database errors into domain exceptions).

### Running tests

* Run all tests: `uv run pytest --reuse-db -s --maxfail=1 tests/`
* ALWAYS prefer specifying test files for efficiency
* Run test commands outside the command sandbox: it blocks localhost TCP, so `Connection refused` from a local service means the sandbox, not a stopped server.
* `tests/api/test_conversations.py` spawns real agent processes instead of mocking them, so it
  needs the agent's virtualenv: run `cd ../agent && uv sync` first. Without it the tests skip
  with a reason rather than failing.
    - It also uses `live_server`, because a spawned Runtime replicates its state over a real
      socket and cannot reach an in-process test client.
    - Replication lands *after* the run's event stream has been sent, so read-backs poll
      (`wait_for_replication`) rather than assuming the database is already up to date.