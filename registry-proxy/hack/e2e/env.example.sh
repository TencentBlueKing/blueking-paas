#!/usr/bin/env bash
# 复制为 env.sh 后填写。env.sh 已被 .gitignore 忽略。
# 本文件会进版本库，只放占位，不要写入任何真实凭证。

export CONTAINER_RUNTIME="docker"
export KANIKO_EXECUTOR_IMAGE="gcr.io/kaniko-project/executor:v1.24.0"
export CRANE_IMAGE="gcr.io/go-containerregistry/crane:latest"

# 代理地址。代理监听 127.0.0.1:<端口> 并提供 HTTPS（自签名证书），
# kaniko 与 crane 容器以 host 网络访问，并通过 --add-host 把该主机名解析到 127.0.0.1。
# 不要用 127.0.0.1 或私网 IP 作为代理地址：go-containerregistry 会把它们当作明文 HTTP 访问。
export PROXY_HOST="bkpaas-registry-proxy.test"
export PROXY_PORT="18443"
export ADMIN_PORT="19090"

# 上游凭证来源：逗号分隔的 docker config 文件，按 host 合并，后者覆盖前者。
# 只交给代理进程和脚本里的直连校验，不会挂进任何 kaniko 容器。
export UPSTREAM_DOCKER_CONFIGS="$HOME/.docker/config.json"

# 明文 HTTP 的上游 host，逗号分隔（本地 registry 用）
export INSECURE_UPSTREAMS=""

# ---------- 测试用例（地址由验证负责人决定）----------
# 每个用例跑一次 kaniko：FROM BASE_IMAGE 经代理拉取，产物经代理推到 PUSH_IMAGE；
# 填了 CACHE_REPO 时开启构建缓存并再构建一次，验证缓存命中。
#
# - 三项都写真实仓库地址，不要写代理地址，脚本会改写成经代理的路径
# - BASE_IMAGE 必须带 /bin/sh，Dockerfile 里有 RUN 探针
# - PUSH_IMAGE 必须带 tag；CACHE_REPO 不带 tag
# - BASE_IMAGE 或 PUSH_IMAGE 为空的用例会被跳过
#
# CASES 列出要跑的用例名，每个用例对应一组 CASE_<名>_* 变量。
export CASES="HARBOR BKREPO CROSS"

# 会把 blob 下载重定向到对象存储的上游
export CASE_HARBOR_BASE_IMAGE=""
export CASE_HARBOR_PUSH_IMAGE=""
export CASE_HARBOR_CACHE_REPO=""

# 由仓库直接返回 blob 的上游
export CASE_BKREPO_BASE_IMAGE=""
export CASE_BKREPO_PUSH_IMAGE=""
export CASE_BKREPO_CACHE_REPO=""

# 跨上游：FROM 一个上游的镜像，推到另一个上游，覆盖跨上游 mount 降级。
# 推送目标不能已有 base 的层，否则 kaniko 不会发起 mount。
# 如果上游对其他仓库里已有的 blob 也返回存在，不要把它当作推送目标
export CASE_CROSS_BASE_IMAGE=""
export CASE_CROSS_PUSH_IMAGE=""
export CASE_CROSS_CACHE_REPO=""

# 30-negative.sh 使用哪个用例的推送仓库构造越权请求（越权请求在代理处即被拒绝，不会转发到上游）
export NEGATIVE_CASE="HARBOR"
