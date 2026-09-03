################# App-Spark Agent #################
FROM python:3.14-slim-bookworm
USER root

# tini is PID 1: forwards SIGTERM and reaps zombies
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Same Tencent Cloud pip index as apiserver
RUN mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\n' > ~/.pip/pip.conf

# Install uv in-image; keep it so the later app manager can `uv run`
RUN pip install --no-cache-dir uv==0.10.0

WORKDIR /app

# Project metadata and source
ADD ./pyproject.toml .
ADD ./uv.lock .
ADD ./README.md .
ADD ./app_spark_agent ./app_spark_agent

# Frozen runtime deps; workspace and state must be distinct paths
RUN uv sync --frozen --no-dev \
    && mkdir -p /workspace /state

ENV PATH="/app/.venv/bin:${PATH}"
# Listen on 8090; fall back to these paths when APP_SPARK_AGENT_* is unset
ENV APP_SPARK_AGENT_PORT=8090
ENV APP_SPARK_AGENT_WORKSPACE=/workspace
ENV APP_SPARK_AGENT_STATE_DIR=/state

EXPOSE 8090

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app_spark_agent"]
