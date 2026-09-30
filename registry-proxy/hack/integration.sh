#!/usr/bin/env bash
# 启动本地 registry:2 作为上游，执行 pkg/proxy 的集成测试（-tags integration）。
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

RUNTIME="${CONTAINER_RUNTIME:-docker}"
PORT="${REGISTRY_PROXY_IT_PORT:-25010}"
NAME="registry-proxy-it-upstream"

"$RUNTIME" rm -f "$NAME" >/dev/null 2>&1 || true
"$RUNTIME" run -d --name "$NAME" -p "127.0.0.1:$PORT:5000" "${REGISTRY_IMAGE:-registry:2}" >/dev/null
trap '"$RUNTIME" rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 50); do
  curl -sf "http://127.0.0.1:$PORT/v2/" >/dev/null && break
  sleep 0.2
done

REGISTRY_PROXY_IT_UPSTREAM="127.0.0.1:$PORT" go test -tags integration -count=1 -run Integration -v ./pkg/proxy/
