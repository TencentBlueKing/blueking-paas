#!/usr/bin/env bash
# 各验证脚本共用的环境加载、断言、代理启停、token 签发与 kaniko 调用封装。

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$HERE/.state"
mkdir -p "$STATE_DIR"

ENV_FILE="${E2E_ENV_FILE:-$HERE/env.sh}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "缺少 $ENV_FILE，请先执行: cp env.example.sh env.sh 并填写测试地址" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${CONTAINER_RUNTIME:=docker}"
: "${KANIKO_EXECUTOR_IMAGE:?}"
: "${CRANE_IMAGE:?}"
: "${PROXY_HOST:=bkpaas-registry-proxy.test}"
: "${PROXY_PORT:=18443}"
: "${ADMIN_PORT:=19090}"
: "${UPSTREAM_DOCKER_CONFIGS:=}"
: "${INSECURE_UPSTREAMS:=}"
: "${CASES:=}"
: "${NEGATIVE_CASE:=}"

PROXY_ADDR="$PROXY_HOST:$PROXY_PORT"
CLUSTER="e2e"
AUDIENCE="bkpaas-registry-proxy:$CLUSTER"
PROXY_BIN="$STATE_DIR/registry-proxy"
TOKENTOOL="$STATE_DIR/tokentool"
PROXY_PID_FILE="$STATE_DIR/proxy.pid"
PROXY_LOG="$STATE_DIR/proxy.log"
AUDIT_LOG="$STATE_DIR/audit.jsonl"
PROXY_CONFIG="$STATE_DIR/config.yaml"
SIGNING_KEY="$STATE_DIR/signing.pem"
JWKS="$STATE_DIR/jwks.json"
UPLOAD_KEY="$STATE_DIR/upload.key"
TLS_CRT="$STATE_DIR/tls.crt"
TLS_KEY="$STATE_DIR/tls.key"
UPSTREAM_CONFIG="$STATE_DIR/upstream-docker-config.json"
# 构建 token 的用户名只是占位，代理只看 Basic 的密码段
TOKEN_USER="bkpaas-build"

if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
  C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
else
  C_RED=''; C_GREEN=''; C_YELLOW=''; C_BOLD=''; C_OFF=''
fi

PASS_COUNT=0
FAIL_COUNT=0

section() { printf '\n%s== %s ==%s\n' "$C_BOLD" "$1" "$C_OFF"; }
info()    { printf '   %s\n' "$1"; }

pad() {
  python3 -c 'import sys, unicodedata
text, width = sys.argv[1], int(sys.argv[2])
shown = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
sys.stdout.write(text + " " * max(1, width - shown))' "$1" "$2"
}

expect() {
  local label="$1" actual="$2"; shift 2
  local want
  for want in "$@"; do
    if [[ "$actual" == "$want" ]]; then
      printf '%s  PASS%s  %s%s\n' "$C_GREEN" "$C_OFF" "$(pad "$label" 52)" "$actual"
      PASS_COUNT=$((PASS_COUNT + 1))
      return 0
    fi
  done
  printf '%s  FAIL%s  %s%s（期望 %s）\n' "$C_RED" "$C_OFF" "$(pad "$label" 52)" "$actual" "$*"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  return 1
}

observe() {
  printf '%s  NOTE%s  %s%s\n' "$C_YELLOW" "$C_OFF" "$(pad "$1" 52)" "$2"
}

summary() {
  printf '\n%s—— %s：%d 通过，%d 失败 ——%s\n' \
    "$C_BOLD" "${1:-结果}" "$PASS_COUNT" "$FAIL_COUNT" "$C_OFF"
  [[ "$FAIL_COUNT" -eq 0 ]]
}

rt() { "$CONTAINER_RUNTIME" "$@"; }

relax_perms() {
  local target="$1"
  [[ -e "$target" ]] || return 0
  rt run --rm -v "$target:/target" busybox:1.36 chmod -R a+rX /target >/dev/null 2>&1 || true
}

rm_as_root() {
  local target="$1"
  [[ -e "$target" ]] || return 0
  rt run --rm -v "$(dirname "$target"):/target" busybox:1.36 \
    rm -rf "/target/$(basename "$target")" >/dev/null 2>&1 || rm -rf "$target" 2>/dev/null || true
}

# ---------- 镜像引用 ----------

host_of() { printf '%s' "${1%%/*}"; }

# 去掉 host 与 tag，只保留仓库路径
path_of() {
  local rest="${1#*/}"
  rest="${rest%%@*}"
  local last="${rest##*/}"
  [[ "$last" == *:* ]] && rest="${rest%:*}"
  printf '%s' "$rest"
}

tag_of() {
  local last="${1##*/}"
  if [[ "$last" == *:* ]]; then printf '%s' "${last##*:}"; else printf 'latest'; fi
}

# 上游别名由主机名推导：转小写后把 . 与 : 替换为 -
upstream_alias() { local n; n="$(tr '[:upper:]' '[:lower:]' <<<"$1")"; n="${n//./-}"; printf '%s' "${n//:/-}"; }

# 真实仓库地址 -> 经代理访问的地址（不含 tag）
proxy_repo() {
  printf '%s/%s/%s' "$PROXY_ADDR" "$(upstream_alias "$(host_of "$1")")" "$(path_of "$1")"
}

# 真实仓库地址 -> 客户端视角的仓库路径（token 授权里用的就是它）
client_repo() {
  printf '%s/%s' "$(upstream_alias "$(host_of "$1")")" "$(path_of "$1")"
}

case_var() { local v="CASE_${1}_${2}"; printf '%s' "${!v:-}"; }

is_insecure_upstream() {
  [[ ",$INSECURE_UPSTREAMS," == *",$1,"* ]]
}

# 所有用例涉及到的上游 host，去重
all_upstream_hosts() {
  local c f v
  for c in $CASES; do
    for f in BASE_IMAGE PUSH_IMAGE CACHE_REPO; do
      v="$(case_var "$c" "$f")"
      [[ -n "$v" ]] && host_of "$v" && echo
    done
  done | sort -u | sed '/^$/d'
}

# ---------- 代理 ----------

stop_proxy() {
  if [[ -f "$PROXY_PID_FILE" ]]; then
    kill "$(cat "$PROXY_PID_FILE")" 2>/dev/null || true
    rm -f "$PROXY_PID_FILE"
    sleep 0.5
  fi
}

prepare_keys() {
  [[ -f "$SIGNING_KEY" ]] || "$TOKENTOOL" keygen -out "$SIGNING_KEY"
  "$TOKENTOOL" jwks -out "$JWKS" "$SIGNING_KEY"
  [[ -f "$UPLOAD_KEY" ]] || (umask 077; head -c 48 /dev/urandom | base64 >"$UPLOAD_KEY")
  if [[ ! -f "$TLS_CRT" ]]; then
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 30 \
      -subj "/CN=$PROXY_HOST" -addext "subjectAltName=DNS:$PROXY_HOST,IP:127.0.0.1" \
      -keyout "$TLS_KEY" -out "$TLS_CRT" >/dev/null 2>&1
  fi
}

start_proxy() {
  [[ -x "$PROXY_BIN" && -x "$TOKENTOOL" ]] || { echo "代理未编译，请先执行 bash 00-build.sh" >&2; return 1; }
  stop_proxy
  prepare_keys

  local configs=()
  if [[ -n "$UPSTREAM_DOCKER_CONFIGS" ]]; then
    IFS=',' read -ra configs <<<"$UPSTREAM_DOCKER_CONFIGS"
    info "上游凭证覆盖的 host：$(python3 "$HERE/helpers.py" merge-configs "$UPSTREAM_CONFIG" "${configs[@]}")"
  else
    (umask 077; printf '{"auths":{}}' >"$UPSTREAM_CONFIG")
  fi

  local ups="" h scheme n=0
  while read -r h; do
    [[ -z "$h" ]] && continue
    scheme=https; is_insecure_upstream "$h" && scheme=http
    ups+="  - alias: $(upstream_alias "$h")"$'\n'"    url: $scheme://$h"$'\n'
    n=$((n + 1))
  done < <(all_upstream_hosts)
  if [[ "$n" -eq 0 ]]; then
    echo "没有可用的上游：请在 env.sh 中至少填写一个用例的地址" >&2
    return 1
  fi

  cat >"$PROXY_CONFIG" <<EOF
listen: "127.0.0.1:$PROXY_PORT"
admin_listen: "127.0.0.1:$ADMIN_PORT"
tls:
  cert_file: $TLS_CRT
  key_file: $TLS_KEY
audience: "$AUDIENCE"
jwks_file: $JWKS
upstream_docker_config_file: $UPSTREAM_CONFIG
upload_session:
  key_file: $UPLOAD_KEY
upstreams:
$ups
EOF

  nohup "$PROXY_BIN" -config "$PROXY_CONFIG" >>"$AUDIT_LOG" 2>"$PROXY_LOG" &
  echo $! >"$PROXY_PID_FILE"
  disown

  local i
  for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$ADMIN_PORT/readyz" >/dev/null 2>&1; then
      info "代理已启动 https://$PROXY_ADDR（监听 127.0.0.1:$PROXY_PORT），上游：$(grep -c 'alias:' "$PROXY_CONFIG") 个"
      return 0
    fi
    sleep 0.2
  done
  echo "代理启动失败，日志：" >&2
  cat "$PROXY_LOG" >&2
  return 1
}

# pcurl：访问代理，主机名解析到 127.0.0.1，并跳过自签名证书校验
pcurl() { curl -sk --resolve "$PROXY_ADDR:127.0.0.1" "$@"; }

# issue_token <输出文件> [--expired] [--audience <aud>] [--key <私钥>] -- <helpers.py claims 参数...>
issue_token() {
  local out="$1"; shift
  local extra=() key="$SIGNING_KEY" aud="$AUDIENCE"
  while [[ $# -gt 0 && "$1" != "--" ]]; do
    case "$1" in
      --expired) extra+=(-expired); shift ;;
      --audience) aud="$2"; shift 2 ;;
      --key) key="$2"; shift 2 ;;
      *) echo "issue_token: unknown option $1" >&2; return 1 ;;
    esac
  done
  shift
  python3 "$HERE/helpers.py" claims "$out.claims.json" "$@"
  (umask 077; "$TOKENTOOL" sign -key "$key" -claims "$out.claims.json" -audience "$aud" \
    ${extra[@]+"${extra[@]}"} >"$out")
}

# make_builder_config <token 文件> <输出目录>：构建容器唯一能看到的凭证
make_builder_config() {
  local token_file="$1" dir="$2"
  mkdir -p "$dir"
  python3 -c 'import base64, json, sys
host, user, token = sys.argv[1], sys.argv[2], open(sys.argv[3]).read().strip()
auth = base64.b64encode(f"{user}:{token}".encode()).decode()
json.dump({"auths": {host: {"username": user, "password": token, "auth": auth}}}, open(sys.argv[4], "w"))' \
    "$PROXY_ADDR" "$TOKEN_USER" "$token_file" "$dir/config.json"
  chmod 644 "$dir/config.json"
}

# crane_digest <docker config 文件> <镜像> [--insecure]
crane_digest() {
  local cfg="$1" image="$2"; shift 2
  # crane 镜像的 HOME 不是 /root，挂到 /root/.docker 不会被读取；
  # 上游凭证文件权限为 600，以当前用户运行 crane 才能读取
  rt run --rm --network host --add-host "$PROXY_HOST:127.0.0.1" --user "$(id -u):$(id -g)" \
    -e DOCKER_CONFIG=/docker \
    -v "$cfg:/docker/config.json:ro" \
    "$CRANE_IMAGE" digest "$image" "$@" 2>/dev/null
}

print_redacted_tail() {
  local file="$1"; shift
  tail -n "${TAIL_LINES:-40}" "$file" | python3 "$HERE/helpers.py" redact "$UPSTREAM_CONFIG" "$@" | sed 's/^/      /'
}
