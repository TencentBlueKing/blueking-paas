#!/usr/bin/env bash
# 协议细节与越权的负面用例。越权请求在代理处即被拒绝，不会转发到上游；
# 只有「凭证不外泄」一节会访问上游：读 base image manifest，以及用构建 token 直连上游尝试发起上传（预期被拒）。
# 用法：bash 30-negative.sh [用例名]，缺省取 NEGATIVE_CASE。

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

C="${1:-$NEGATIVE_CASE}"
PUSH="$(case_var "$C" PUSH_IMAGE)"
BASE="$(case_var "$C" BASE_IMAGE)"
if [[ -z "$C" || -z "$PUSH" || -z "$BASE" ]]; then
  echo "NEGATIVE_CASE=$C 对应的 BASE_IMAGE / PUSH_IMAGE 未填写" >&2
  exit 1
fi

section "启动代理"
start_proxy || exit 1

DIR="$STATE_DIR/negative"
mkdir -p "$DIR"
REPO="$(client_repo "$PUSH")"
TAG="$(tag_of "$PUSH")"
BASE_REPO="$(client_repo "$BASE")"
BASE_TAG="$(tag_of "$BASE")"
PULL_PREFIX="$(upstream_alias "$(host_of "$BASE")")/"

issue_token "$DIR/valid" -- --sub e2e-negative --pull "$PULL_PREFIX" --push "$REPO=$TAG"
issue_token "$DIR/nopull" -- --sub e2e-negative-nopull --push "$REPO=$TAG"
issue_token "$DIR/expired" --expired -- --sub e2e-negative-expired --push "$REPO=$TAG"
issue_token "$DIR/other-aud" --audience "bkpaas-registry-proxy:other-cluster" -- --sub e2e-negative-aud --push "$REPO=$TAG"
[[ -f "$DIR/rogue.pem" ]] || "$TOKENTOOL" keygen -out "$DIR/rogue.pem"
issue_token "$DIR/forged" --key "$DIR/rogue.pem" -- --sub e2e-negative-forged --push "$REPO=$TAG"

P="https://$PROXY_ADDR"
ACCEPT='application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json'

# req <token 文件，空表示不带凭证> <方法> <路径> [curl 参数...]，输出状态码
req() {
  local tf="$1" m="$2" p="$3"; shift 3
  local auth=()
  [[ -n "$tf" ]] && auth=(-u "$TOKEN_USER:$(cat "$tf")")
  pcurl -o /dev/null -w '%{http_code}' -X "$m" ${auth[@]+"${auth[@]}"} "$@" "$P$p"
}

# body <token 文件> <方法> <路径>：输出错误响应体中的拒绝原因
deny_of() {
  local tf="$1" m="$2" p="$3"
  pcurl -X "$m" -u "$TOKEN_USER:$(cat "$tf")" "$P$p" |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["errors"][0]["message"])' 2>/dev/null
}

section "认证与 /v2/ 质询"
expect "无凭证访问 /v2/" "$(req "" GET /v2/)" 401
chal="$(pcurl -D - -o /dev/null "$P/v2/" | tr -d '\r' | grep -i '^www-authenticate:' | cut -d' ' -f2-)"
expect "/v2/ 质询方式（客户端据此带上 token）" "$chal" 'Basic realm="bkpaas-registry-proxy"'
expect "有效 token 访问 /v2/" "$(req "$DIR/valid" GET /v2/)" 200
expect "无凭证拉推送仓库 manifest" "$(req "" GET "/v2/$REPO/manifests/$TAG")" 401
expect "伪造签名的 token" "$(req "$DIR/forged" GET "/v2/$REPO/manifests/$TAG")" 401
expect "过期 token" "$(req "$DIR/expired" GET "/v2/$REPO/manifests/$TAG")" 401
expect "其他集群的 token" "$(req "$DIR/other-aud" GET "/v2/$REPO/manifests/$TAG")" 401

section "授权（在代理处拒绝，不转发上游）"
expect "推送未授权的 tag" \
  "$(req "$DIR/valid" PUT "/v2/$REPO/manifests/e2e-not-granted" \
      -H 'Content-Type: application/vnd.oci.image.manifest.v1+json' --data '{}')" 403
expect "拒绝原因带固定标记" "$(deny_of "$DIR/valid" PUT "/v2/$REPO/manifests/e2e-not-granted")" \
  "bkpaas-registry-proxy: tag_not_granted"
expect "向未授权仓库发起上传" "$(req "$DIR/valid" POST "/v2/${REPO}-not-granted/blobs/uploads/")" 403
expect "删除已授权仓库的 manifest" "$(req "$DIR/valid" DELETE "/v2/$REPO/manifests/$TAG")" 403
expect "访问未配置的上游" "$(req "$DIR/valid" GET /v2/unknown-example-com/foo/bar/manifests/latest)" 403
expect "token 不含 pull 授权时拉 base image" \
  "$(req "$DIR/nopull" GET "/v2/$BASE_REPO/manifests/$BASE_TAG" -H "Accept: $ACCEPT")" 403
expect "枚举仓库 /v2/_catalog" "$(req "$DIR/valid" GET /v2/_catalog)" 404
expect "伪造上传会话 token" "$(req "$DIR/valid" PATCH "/v2/$REPO/blobs/uploads/forged.session" --data x)" 403
expect "伪造上传会话的拒绝原因" "$(deny_of "$DIR/valid" PATCH "/v2/$REPO/blobs/uploads/forged.session")" \
  "bkpaas-registry-proxy: invalid_upload_session"

section "凭证不外泄（访问上游）"
pcurl -D "$DIR/headers.txt" -o "$DIR/body.txt" -u "$TOKEN_USER:$(cat "$DIR/valid")" \
  -H "Accept: $ACCEPT" "$P/v2/$BASE_REPO/manifests/$BASE_TAG"
code="$(head -n1 "$DIR/headers.txt" | awk '{print $2}')"
expect "经代理拉 base image manifest" "$code" 200
cat "$DIR/headers.txt" "$DIR/body.txt" >"$DIR/response.txt"
expect "响应中上游凭证出现次数" "$(python3 "$HERE/helpers.py" leak-hits "$UPSTREAM_CONFIG" "$DIR/response.txt")" 0
expect "响应头不透传上游质询" "$(grep -ci '^www-authenticate:' "$DIR/headers.txt")" 0
expect "响应头不透传上游 Cookie" "$(grep -ci '^set-cookie:' "$DIR/headers.txt")" 0

insecure=""
is_insecure_upstream "$(host_of "$PUSH")" && insecure=1
probe="$(python3 "$HERE/helpers.py" upstream-token-probe "$(host_of "$PUSH")" "$(path_of "$PUSH")" "$DIR/valid" "$insecure")"
# 换 token 被拒，或换到的 token 无法上传，都说明构建 token 在上游不具备推送能力
expect "拿构建 token 直连上游推送" "$probe" token-401 token-403 token-200/upload-401 token-200/upload-403 \
  basic/upload-401 basic/upload-403 anonymous-200

section "审计"
expect "审计日志中构建 token 出现次数" "$(python3 "$HERE/helpers.py" count-in "$DIR/valid" "$AUDIT_LOG")" 0
expect "审计日志中上游凭证出现次数" "$(python3 "$HERE/helpers.py" leak-hits "$UPSTREAM_CONFIG" "$AUDIT_LOG")" 0
observe "审计日志记录的拒绝次数（含 sub 与原因）" "$(python3 "$HERE/helpers.py" audit-count "$AUDIT_LOG" e2e-negative deny)"

stop_proxy
summary "负面用例"
