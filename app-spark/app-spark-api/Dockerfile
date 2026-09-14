# Build from app-spark/: docker build -f app-spark-api/Dockerfile -t app-spark-api:0.1.0 .
FROM python:3.14-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git tini \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.10.0

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app/app-spark-api
COPY app-spark-api/pyproject.toml app-spark-api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# local_process spawns Agent processes inside this API container. It needs the sibling
# project AND its own preinstalled virtualenv; --no-sync must never download on a request.
WORKDIR /app/agent
COPY agent/pyproject.toml agent/uv.lock agent/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY agent/app_spark_agent ./app_spark_agent
RUN uv sync --frozen --no-dev

WORKDIR /app/app-spark-api
COPY app-spark-api/manage.py app-spark-api/README.md ./
COPY app-spark-api/app_spark_api ./app_spark_api
RUN mkdir -p /data/app-spark

EXPOSE 8000
# Reap Agent children and forward shutdown signals to the API process.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uv", "run", "--no-sync", "uvicorn", "app_spark_api.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-graceful-shutdown", "30"]
