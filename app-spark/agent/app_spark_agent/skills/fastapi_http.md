# FastAPI HTTP application

Write the user-facing application as a FastAPI app exported from main.py as app (import path main:app).

Read the listen port from the environment variable APP_SPARK_AGENT_APP_PORT. Bind to that port. Do not hard-code a different listen port.

Do not start or keep the process running yourself. Do not use the shell to host a long-running server. The control plane launches the application after the user asks to launch it.

Do not align this application with the BlueKing or PaaS application framework in this period. A plain FastAPI HTTP app is enough.
