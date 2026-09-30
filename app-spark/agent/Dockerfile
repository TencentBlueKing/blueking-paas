# check=skip=InvalidDefaultArgInFrom
################# App-Spark Agent sandbox image #################
# Registered as an e2b template: the container only runs envd, and the API service starts the
# Agent through envd once it has injected the Agent's credentials and configuration.

# The cube base image that ships envd and its entrypoint. No default on purpose: envd must match
# the platform's ENVD_REF, so every build names the tag it was made against.
ARG CUBE_BASE_ENVD_IMAGE

FROM ${CUBE_BASE_ENVD_IMAGE} AS envd

FROM python:3.14-slim-bookworm
USER root

# tini is PID 1: forwards SIGTERM and reaps zombies.
# git persists the workspace; ca-certificates is what lets it reach an https remote at all.
# sudo keeps the cube convention of a password-less sudo user.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini git ca-certificates sudo \
    && rm -rf /var/lib/apt/lists/*

# Copied rather than built, so envd is byte-for-byte what the platform validated.
COPY --from=envd /usr/bin/envd /usr/bin/envd
COPY --from=envd /usr/local/bin/cube-entrypoint.sh /usr/local/bin/cube-entrypoint.sh

# The cube convention: user (uid 1000) with a home directory and password-less sudo. The API
# service runs the Agent as this user.
RUN useradd --create-home --uid 1000 --shell /bin/bash user \
    && echo 'user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/user \
    && chmod 0440 /etc/sudoers.d/user

# Same Tencent Cloud pip index as apiserver. System-wide rather than under ~root, which user cannot
# read: the Agent and whatever it runs install packages as user.
RUN printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\n' > /etc/pip.conf

# Install uv in-image; keep it so the later app manager can `uv run`
RUN pip install --no-cache-dir uv==0.10.0

WORKDIR /app

# Project metadata and source
ADD ./pyproject.toml .
ADD ./uv.lock .
ADD ./README.md .
ADD ./app_spark_agent ./app_spark_agent

# Frozen runtime deps; workspace and state must be distinct paths under /data.
# All of /data belongs to user, not only the two directories: the Agent also writes its
# application log directly under it (APP_LOG_PATH defaults to /data/app.log).
# Bytecode is compiled here because /app stays root's: user could not write the .pyc files, and
# would recompile on every cold start. Downloads stay off so uv fails rather than fetch a python
# into /root, where user could not run it.
RUN UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev \
    && .venv/bin/python -m compileall -q app_spark_agent \
    && mkdir -p /data/workspace /data/state \
    && chown -R user:user /data

# Only for a local `docker run`: envd gives the processes it starts its own default PATH, so the
# API service starts the Agent with the venv's python by absolute path.
ENV PATH="/app/.venv/bin:${PATH}"
# Listen on 8090; fall back to these paths when APP_SPARK_AGENT_* is unset
ENV APP_SPARK_AGENT_PORT=8090
ENV APP_SPARK_AGENT_WORKSPACE=/data/workspace
ENV APP_SPARK_AGENT_STATE_DIR=/data/state
# The platform probes envd on this port, and expects it to answer within about a second.
ENV ENVD_PORT=49983

EXPOSE 49983 8090

# No CMD: the entrypoint then keeps envd in the foreground, and the Agent starts only when the
# API service asks envd to start it. A CMD would start it here, before it has any credentials.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cube-entrypoint.sh"]
