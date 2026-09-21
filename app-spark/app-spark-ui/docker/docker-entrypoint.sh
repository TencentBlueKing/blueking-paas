#!/bin/sh
# 容器启动入口：读取公开配置、校验 URL、恢复静态文件、替换运行时占位符，
# 最后 exec 传入的命令，使 Nginx 直接接收容器停止信号。
#
# 仅支持 BK_SITE_URL、BK_LOGIN_URL、BK_TEMPLATE_URL；进程环境优先于 ENV_FILE。
# BK_LOGIN_URL 必填；根路径默认为空，未配置的预览地址使用 about:blank。
# 配置文件作为数据读取，不执行 shell 表达式，也不展开其中的变量。
#
# 使用样例（镜像默认执行 nginx -g 'daemon off;'）：
#   docker run --rm -p 5000:5000 \
#     -e BK_LOGIN_URL=https://login.example.com \
#     -e BK_SITE_URL=/spark app-spark-ui:latest
#
# 使用配置文件（默认读取 /env/.env，可用 ENV_FILE 指定其他路径）：
#   docker run --rm -p 5000:5000 \
#     -v "$PWD/runtime.env:/env/.env:ro" app-spark-ui:latest
#
# 镜像内仅注入配置并检查 Nginx 语法：
#   BK_LOGIN_URL=https://login.example.com /docker-entrypoint.sh nginx -t
set -eu

readonly ORIGINAL_HTML_DIR=/opt/app-spark/html
readonly HTML_DIR=/usr/share/nginx/html
readonly NGINX_TEMPLATE=/opt/app-spark/nginx-default.conf.template
readonly NGINX_CONFIG=/etc/nginx/conf.d/default.conf

log() {
    printf '[docker-entrypoint] %s\n' "$*"
}

fail() {
    log "$*" >&2
    exit 1
}

# 与参考镜像一致：进程环境（包括显式空值）优先于 ENV_FILE，不执行文件内容。
load_env_file() {
    ENV_FILE=${ENV_FILE:-/env/.env}
    if [ ! -f "$ENV_FILE" ]; then
        return
    fi

    # 接受空行、整行注释、带引号的值及末尾没有换行符的最后一行。
    while IFS= read -r env_line || [ -n "$env_line" ]; do
        env_line=$(printf '%s' "$env_line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        case "$env_line" in
            ''|'#'*) continue ;;
        esac
        case "$env_line" in
            *=*) ;;
            *) fail "Invalid ENV_FILE assignment" ;;
        esac

        env_key=$(printf '%s' "$env_line" | sed 's/[[:space:]]*=.*//')
        env_value=$(printf '%s' "$env_line" | sed 's/^[^=]*=[[:space:]]*//')
        case "$env_key" in
            BK_SITE_URL|BK_LOGIN_URL|BK_TEMPLATE_URL) ;;
            *) continue ;;
        esac
        case "$env_value" in
            \"*\")
                env_value=${env_value#\"}
                env_value=${env_value%\"}
                ;;
            \'*\')
                env_value=${env_value#\'}
                env_value=${env_value%\'}
                ;;
        esac
        if ! printenv "$env_key" >/dev/null 2>&1; then
            export "$env_key=$env_value"
        fi
    done < "$ENV_FILE"
}

# 统一默认值与路径格式，后续校验和文件注入使用同一份配置。
normalize_runtime_config() {
    BK_SITE_URL=${BK_SITE_URL:-}
    BK_SITE_URL=${BK_SITE_URL%/}
    BK_LOGIN_URL=${BK_LOGIN_URL:-}
    # Webpack 会折叠带非空占位符的 || 分支；空预览在启动时显式变为 about:blank。
    BK_TEMPLATE_URL=${BK_TEMPLATE_URL:-about:blank}
    export BK_SITE_URL BK_LOGIN_URL BK_TEMPLATE_URL
}

# 值进入 HTML/JS 字符串与 Nginx 路径。仅接受 URL，特殊字符必须先做百分号编码。
# 例如查询值中的单引号使用 %27；不能只转义 sed 后直接写入 JS。
validate_url() {
    case "$2" in
        *"'"*|*'"'*|*'\'*|*'`'*|*'<'*|*'>'*|*'__APP_SPARK_RT_'*|*'
'*)
            fail "$1 contains unsafe URL characters; use percent encoding"
            ;;
    esac
    if printf '%s' "$2" | LC_ALL=C grep -q '[[:space:][:cntrl:]]'; then
        fail "$1 contains whitespace or control characters; use percent encoding"
    fi
}

# 在修改任何部署文件前，校验字符安全性和各配置项支持的 URL 形式。
validate_runtime_config() {
    validate_url BK_SITE_URL "$BK_SITE_URL"
    validate_url BK_LOGIN_URL "$BK_LOGIN_URL"
    validate_url BK_TEMPLATE_URL "$BK_TEMPLATE_URL"

    if ! printf '%s\n' "$BK_SITE_URL" | grep -Eq '^(/[A-Za-z0-9_-]+)*$'; then
        fail "BK_SITE_URL must be empty or a path such as /spark"
    fi
    case "$BK_LOGIN_URL" in
        http://?*|https://?*) ;;
        *) fail "BK_LOGIN_URL must be an absolute HTTP(S) login URL" ;;
    esac
    case "$BK_TEMPLATE_URL" in
        about:blank|http://?*|https://?*|/[!/]*) ;;
        *) fail "BK_TEMPLATE_URL must be an HTTP(S) URL or a root-relative path" ;;
    esac
}

# 从只读原件恢复，避免容器 restart 后已经消失的占位符无法重新注入。
restore_runtime_files() {
    cp -R "$ORIGINAL_HTML_DIR/." "$HTML_DIR/"
    cp "$NGINX_TEMPLATE" "$NGINX_CONFIG"

    # 根路径无需去除前缀；在替换占位符前移除规则，避免依赖 Nginx 对原地 rewrite 的处理。
    if [ -z "$BK_SITE_URL" ]; then
        sed -i '/^[[:space:]]*rewrite .*__APP_SPARK_RT_BK_SITE_URL__/d' "$NGINX_CONFIG"
    fi
}

# 使用子 shell 隔离替换变量和清理 trap，函数结束后不影响最终 exec 的服务。
inject_runtime_config() (
    # 只转义 sed 替换串的特殊字符；URL 字符安全性已由前面的校验保证。
    expression=''
    for key in BK_SITE_URL BK_LOGIN_URL BK_TEMPLATE_URL; do
        value=$(printenv "$key" | sed 's/[\&|]/\\&/g')
        expression="${expression}s|__APP_SPARK_RT_${key}__|${value}|g;"
    done

    # 使用文件列表而非空白分词，确保包含空格的资源文件名也能正确处理。
    file_list=$(mktemp)
    trap 'rm -f "$file_list"' EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    grep -rl '__APP_SPARK_RT_' "$HTML_DIR" "$NGINX_CONFIG" > "$file_list"
    while IFS= read -r file; do
        sed -i "$expression" "$file"
    done < "$file_list"

    # 构建产物若含未知占位符，停止启动，避免向浏览器返回半成品配置。
    if grep -rq '__APP_SPARK_RT_' "$HTML_DIR" "$NGINX_CONFIG"; then
        fail "Unresolved runtime placeholders"
    fi
)

main() {
    # 1. 合并配置并完成校验，失败时保留部署文件原状。
    load_env_file
    normalize_runtime_config
    validate_runtime_config

    # 2. 每次启动都从原始构建产物重新注入，包括容器重启和子路径变更。
    restore_runtime_files
    inject_runtime_config

    # 3. 将进程控制权交给调用方指定的命令（镜像默认为前台 Nginx）。
    log 'Runtime configuration injected; starting service'
    exec "$@"
}

main "$@"
