#!/bin/sh
set -eu

log() { printf '[docker-entrypoint] %s\n' "$*"; }
fail() { log "$*" >&2; exit 1; }

# 与参考镜像一致：进程环境（包括显式空值）优先于 ENV_FILE，不执行文件内容。
ENV_FILE=${ENV_FILE:-/env/.env}
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        case "$line" in ''|'#'*) continue ;; esac
        case "$line" in *=*) ;; *) fail "Invalid ENV_FILE assignment" ;; esac
        key=$(printf '%s' "$line" | sed 's/[[:space:]]*=.*//')
        value=$(printf '%s' "$line" | sed 's/^[^=]*=[[:space:]]*//')
        case "$key" in
            BK_SITE_URL|BK_LOGIN_URL|BK_TEMPLATE_URL) ;;
            *) continue ;;
        esac
        case "$value" in
            \"*\") value=${value#\"}; value=${value%\"} ;;
            \'*\') value=${value#\'}; value=${value%\'} ;;
        esac
        if ! printenv "$key" >/dev/null 2>&1; then
            export "$key=$value"
        fi
    done < "$ENV_FILE"
fi

BK_SITE_URL=${BK_SITE_URL:-}
BK_SITE_URL=${BK_SITE_URL%/}
BK_LOGIN_URL=${BK_LOGIN_URL:-}
# Webpack 会折叠带非空占位符的 || 分支；空预览在启动时显式变为 about:blank。
BK_TEMPLATE_URL=${BK_TEMPLATE_URL:-about:blank}
export BK_SITE_URL BK_LOGIN_URL BK_TEMPLATE_URL

# 值进入 HTML/JS 字符串与 Nginx 路径。仅接受 URL，特殊字符必须先做百分号编码。
# 例如查询值中的单引号使用 %27；不能只转义 sed 后直接写入 JS。
validate_url() {
    key=$1
    value=$2
    case "$value" in
        *"'"*|*'"'*|*'\'*|*'`'*|*'<'*|*'>'*|*'__APP_SPARK_RT_'*|*'
'*)
            fail "$key contains unsafe URL characters; use percent encoding" ;;
    esac
    if printf '%s' "$value" | LC_ALL=C grep -q '[[:space:][:cntrl:]]'; then
        fail "$key contains whitespace or control characters; use percent encoding"
    fi
}
validate_url BK_SITE_URL "$BK_SITE_URL"
validate_url BK_LOGIN_URL "$BK_LOGIN_URL"
validate_url BK_TEMPLATE_URL "$BK_TEMPLATE_URL"
printf '%s\n' "$BK_SITE_URL" | grep -Eq '^(/[A-Za-z0-9_-]+)*$' \
    || fail "BK_SITE_URL must be empty or a path such as /spark"
case "$BK_LOGIN_URL" in
    http://?*|https://?*) ;;
    *) fail "BK_LOGIN_URL must be an absolute HTTP(S) login URL" ;;
esac
case "$BK_TEMPLATE_URL" in
    about:blank|http://?*|https://?*|/[!/]*) ;;
    *) fail "BK_TEMPLATE_URL must be an HTTP(S) URL or a root-relative path" ;;
esac

# 从只读原件恢复，避免容器 restart 后已经消失的占位符无法重新注入。
cp -R /opt/app-spark/html/. /usr/share/nginx/html/
cp /opt/app-spark/nginx-default.conf.template /etc/nginx/conf.d/default.conf
expression=''
for key in BK_SITE_URL BK_LOGIN_URL BK_TEMPLATE_URL; do
    value=$(printenv "$key" | sed 's/[\&|]/\\&/g')
    expression="${expression}s|__APP_SPARK_RT_${key}__|${value}|g;"
done
file_list=$(mktemp)
trap 'rm -f "$file_list"' EXIT HUP INT TERM
grep -rl '__APP_SPARK_RT_' /usr/share/nginx/html /etc/nginx/conf.d/default.conf > "$file_list"
while IFS= read -r file; do
    sed -i "$expression" "$file"
done < "$file_list"
if grep -rq '__APP_SPARK_RT_' /usr/share/nginx/html /etc/nginx/conf.d/default.conf; then
    fail "Unresolved runtime placeholders"
fi
rm -f "$file_list"
trap - EXIT HUP INT TERM
log 'Runtime configuration injected; starting service'
exec "$@"
