## Context

You are in the apiserver repo, helping implement features, fix bugs, and refactor existing code.

## Source code

* apiserver is a REST API service implemented in Python and Django REST Framework.
* The main project in `paasng/`.
* Unit tests are placed in 'paasng/tests' directory, following pytest conventions.
* Some design notes can be found in `design_notes/`.
* When writing tests, always refer to `paasng/tests/conftest.py` for guidance on common fixtures.

## Coding style

* For Python files, follow PEP-8.
* For Python files, run `ruff format` to format after edits.

### Running our tests

* Run all tests: `pytest --reuse-db -s --maxfail=1 tests/`
* Run some tests: `pytest --reuse-db -s --maxfail=1 tests/filename.py`
* ALWAYS prefer specifying test files for efficiency.
