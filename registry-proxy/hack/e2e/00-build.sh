#!/usr/bin/env bash
# 编译代理与 token 工具到 .state/
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HERE/.state"
cd "$HERE/../.."
CGO_ENABLED=0 go build -trimpath -o "$HERE/.state/registry-proxy" ./cmd/registry-proxy
go build -o "$HERE/.state/tokentool" ./hack/tokentool
echo "已编译：$HERE/.state/registry-proxy、$HERE/.state/tokentool"
