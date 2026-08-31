"""End-to-end scenarios against a real Runtime process and the real model.

Everything else in the suite scripts the model; these are the tests that do not. A uvicorn
process is started exactly the way a deployment starts one, and every assertion travels over
HTTP -- which is why this is the only place where "the summary survived the next request" or
"a restarted process finds its own state" can actually be observed.

One file per scenario, and one scenario per file: a live turn costs a real model call, so each
file tells a single connected story rather than a handful of independent cases.

They are marked ``live`` and need an API key::

    uv run pytest -m live -s

``-s`` is not optional in practice. Each call narrates itself through :mod:`tests.e2e.console`, so
the console shows the request, the tool calls, and the model's answer as it is being written --
without it a passing run looks exactly like a hung one for minutes at a time.
"""
