#!/usr/bin/env bash
# 经代理跑 kaniko：FROM 经代理拉取，产物经代理推送，可选构建缓存。
# kaniko 参数与构建链路展开后的参数一致；构建容器只拿到构建 token，
# 同时验证 RUN 里看不到任何上游凭证。

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

section "启动代理"
start_proxy || exit 1

# REGISTRY_MAP=<上游主机>=<代理地址>/<别名>，每个上游主机一项
REGISTRY_MAPS=()
while read -r h; do
  [[ -z "$h" ]] && continue
  REGISTRY_MAPS+=(--registry-map "$h=$PROXY_ADDR/$(upstream_alias "$h")")
done < <(all_upstream_hosts)

# kaniko_run <用例目录> <日志文件> <推送地址> [缓存仓库]
kaniko_run() {
  local dir="$1" log="$2" push="$3" cache="${4:-}"
  local extra=()
  [[ -n "$cache" ]] && extra=(--cache --cache-repo "$(proxy_repo "$cache")")
  rt run --rm --network host --add-host "$PROXY_HOST:127.0.0.1" \
    -v "$dir/ctx:/workspace:ro" \
    -v "$dir/docker:/kaniko/.docker:ro" \
    -v "$dir/out:/out" \
    "$KANIKO_EXECUTOR_IMAGE" \
    --dockerfile /workspace/Dockerfile \
    --context dir:///workspace/ \
    --destination "$(proxy_repo "$push"):$(tag_of "$push")" \
    "${REGISTRY_MAPS[@]}" \
    --skip-default-registry-fallback \
    --skip-tls-verify-registry "$PROXY_ADDR" \
    --digest-file /out/digest \
    --ignore-path /product_uuid \
    --verbosity info \
    ${extra[@]+"${extra[@]}"} >"$log" 2>&1
}

run_case() {
  local c="$1" base push cache
  base="$(case_var "$c" BASE_IMAGE)"
  push="$(case_var "$c" PUSH_IMAGE)"
  cache="$(case_var "$c" CACHE_REPO)"

  section "用例 $c"
  if [[ -z "$base" || -z "$push" ]]; then
    info "未填写 CASE_${c}_BASE_IMAGE / CASE_${c}_PUSH_IMAGE，跳过"
    return
  fi
  info "FROM   $base"
  info "推送到 $push"
  [[ -n "$cache" ]] && info "缓存   $cache"

  local dir="$STATE_DIR/cases/$c"
  rm_as_root "$dir"
  mkdir -p "$dir/ctx" "$dir/out"
  local sub tag push_repo
  sub="e2e-$(tr '[:upper:]' '[:lower:]' <<<"$c")-$(date +%s)"
  tag="$(tag_of "$push")"
  push_repo="$(client_repo "$push")"

  # pull 为 base 所在上游，pull_deny 为产物仓库所在的命名空间
  local targs=(--sub "$sub" --pull "$(upstream_alias "$(host_of "$base")")/" --pull-deny "${push_repo%/*}/" --push "$push_repo=$tag")
  [[ -n "$cache" ]] && targs+=(--push "$(client_repo "$cache")=*")
  issue_token "$dir/token" -- "${targs[@]}"
  make_builder_config "$dir/token" "$dir/docker"
  info "构建 ID（审计日志 sub）：$sub"

  # 探针打印 kaniko 进程环境与挂载的 docker config，模拟用户在 Dockerfile 里窃取凭证
  cat >"$dir/ctx/Dockerfile" <<EOF
FROM $base
RUN echo "== probe proc1 environ ==" && (tr '\\0' '\\n' < /proc/1/environ || true) && echo "== probe docker config ==" && (cat /kaniko/.docker/config.json 2>/dev/null || true) && echo && echo "registry-proxy-probe $sub" > /probe.txt
EOF

  local log1="$dir/build-1.log" rc
  kaniko_run "$dir" "$log1" "$push" "$cache"; rc=$?
  if ! expect "kaniko 经代理拉取 base 并推送产物" "$rc" 0; then
    info "构建日志末尾（已脱敏）："
    print_redacted_tail "$log1" "$dir/token"
    info "审计："
    python3 "$HERE/helpers.py" audit-summary "$AUDIT_LOG" "$sub"
    return
  fi

  relax_perms "$dir/out"
  local digest; digest="$(cat "$dir/out/digest" 2>/dev/null)"
  info "产物 digest：$digest"

  local probed=no
  grep -q "== probe docker config ==" "$log1" && probed=yes
  expect "RUN 探针已执行" "$probed" yes
  expect "构建日志中上游凭证出现次数" "$(python3 "$HERE/helpers.py" leak-hits "$UPSTREAM_CONFIG" "$log1")" 0
  observe "构建日志中构建 token 出现次数（可见但受限）" \
    "$(python3 "$HERE/helpers.py" count-in "$dir/token" "$log1")"

  local via_proxy direct insecure=()
  via_proxy="$(crane_digest "$dir/docker/config.json" "$(proxy_repo "$push"):$tag" --insecure)"
  expect "经代理读回的 digest 与构建产物一致" "$([[ -n "$digest" && "$via_proxy" == "$digest" ]] && echo 一致 || echo "不一致:$via_proxy")" 一致
  is_insecure_upstream "$(host_of "$push")" && insecure=(--insecure)
  direct="$(crane_digest "$UPSTREAM_CONFIG" "$push" ${insecure[@]+"${insecure[@]}"})"
  expect "直连上游读回的 digest 与构建产物一致" "$([[ -n "$digest" && "$direct" == "$digest" ]] && echo 一致 || echo "不一致:$direct")" 一致

  if [[ -n "$cache" ]]; then
    local log2="$dir/build-2.log" hit=no
    kaniko_run "$dir" "$log2" "$push" "$cache"; rc=$?
    expect "第二次构建成功" "$rc" 0 || print_redacted_tail "$log2" "$dir/token"
    grep -q "Using caching version of cmd" "$log2" && hit=yes
    expect "第二次构建命中经代理推送的缓存层" "$hit" yes
  fi

  expect "审计中被拒绝的请求数（kaniko 预检的 DELETE 除外）" \
    "$(python3 -c 'import json, sys
print(sum(1 for l in open(sys.argv[1]) for e in [json.loads(l)]
          if e["sub"] == sys.argv[2] and e["deny"] and e["deny"] != "delete_not_allowed"))' "$AUDIT_LOG" "$sub")" 0
  info "审计（经代理的请求与流量）："
  python3 "$HERE/helpers.py" audit-summary "$AUDIT_LOG" "$sub"
}

for c in $CASES; do
  run_case "$c"
done

stop_proxy
summary "kaniko 经代理构建"
