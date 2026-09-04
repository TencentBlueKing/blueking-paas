"""Real Runtime processes driven by a fake model, so they cost nothing and run by default.

Same machinery as :mod:`tests.e2e` -- a uvicorn process started exactly the way a deployment
starts one, every assertion travelling over HTTP -- but with ``APP_SPARK_AGENT_MODEL`` pointed
at a ``fake:`` scenario instead of a real provider.

What this covers that the in-process tests cannot: the Runtime being built by
``create_app_from_settings()`` from environment variables alone. That is the path every
external control plane starts the Runtime through, and it is the path a fake model injected
into ``create_runtime_app(agent=...)`` never touches.
"""
