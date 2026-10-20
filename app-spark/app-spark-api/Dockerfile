# Build from app-spark-api/: docker build -t app-spark-api:0.1.0 .
# Keep the base image, system packages, uv version and command in sync with Dockerfile.dev.
FROM python:3.14-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git procps tini vim \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.10.0

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY manage.py README.md ./
COPY app_spark_api ./app_spark_api
RUN mkdir -p /data/app-spark

EXPOSE 8000
# Forward shutdown signals and reap any child process the API starts.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uv", "run", "--no-sync", "uvicorn", "app_spark_api.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-graceful-shutdown", "30"]
