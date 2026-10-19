#!/usr/bin/env bash
# 本地冒烟：起一个无认证的 registry:2 作为上游，跑完整的 kaniko 与负面用例。
# 只用于调通代理本身，不接触任何真实仓库，也不需要 env.sh。
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$HERE/.state"
mkdir -p "$STATE_DIR"

LOCAL_REGISTRY="127.0.0.1:${LOCAL_REGISTRY_PORT:-25011}"
NAME="registry-proxy-e2e-upstream"
RUNTIME="${CONTAINER_RUNTIME:-docker}"

"$RUNTIME" rm -f "$NAME" >/dev/null 2>&1 || true
"$RUNTIME" run -d --name "$NAME" -p "$LOCAL_REGISTRY:5000" registry:2 >/dev/null
for _ in $(seq 1 30); do
  curl -sf "http://$LOCAL_REGISTRY/v2/" >/dev/null && break
  sleep 0.3
done
"$RUNTIME" tag busybox:1.36 "$LOCAL_REGISTRY/library/busybox:1.36"
"$RUNTIME" push -q "$LOCAL_REGISTRY/library/busybox:1.36" >/dev/null

cat >"$STATE_DIR/env.local.sh" <<EOF
source "$HERE/env.example.sh"
export PROXY_PORT="18444"
export ADMIN_PORT="19091"
export UPSTREAM_DOCKER_CONFIGS=""
export INSECURE_UPSTREAMS="$LOCAL_REGISTRY"
export CASES="LOCAL"
export CASE_LOCAL_BASE_IMAGE="$LOCAL_REGISTRY/library/busybox:1.36"
export CASE_LOCAL_PUSH_IMAGE="$LOCAL_REGISTRY/e2e/app:v1"
export CASE_LOCAL_CACHE_REPO="$LOCAL_REGISTRY/e2e/app/dockerbuild-cache"
export NEGATIVE_CASE="LOCAL"
EOF

rc=0
E2E_ENV_FILE="$STATE_DIR/env.local.sh" bash "$HERE/20-kaniko.sh" || rc=1
E2E_ENV_FILE="$STATE_DIR/env.local.sh" bash "$HERE/30-negative.sh" || rc=1

"$RUNTIME" rm -f "$NAME" >/dev/null 2>&1 || true
exit "$rc"
