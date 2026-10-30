#!/bin/bash
# kubectl exec 等方式不经过 launcher，找不到应用自带的 python。这里先经 launcher 加载应用环境，再执行应用的同名命令。
# launcher 会把参数拼接成字符串交给 bash 执行，因此参数需要先转义。
app_bin="/app/.heroku/python/bin/$(basename "$0")"
if [ ! -x "$app_bin" ]; then
    echo "$(basename "$0"): command not found" >&2
    exit 127
fi

printf -v cmd '%q ' "$app_bin" "$@"
exec /cnb/lifecycle/launcher "$cmd"
