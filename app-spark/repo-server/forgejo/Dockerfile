# repo-server 的生产镜像：官方 Forgejo 加上 init CLI 和它的 uv 虚拟环境。
#
# 镜像与 compose.yaml 钉在同一个 digest 上，升补丁要两边一起改。
# server Deployment 和 init Job 共用本镜像，线上初始化因此跑的是 app_spark_forgejo
# 这一份代码，而不是在 chart 里另写一遍 shell —— 初始化逻辑只有一个实现。
#
# 构建上下文就是本目录：
#   docker build -t app-spark-forgejo:15.0.7 repo-server/forgejo
FROM codeberg.org/forgejo/forgejo:15.0.7@sha256:1f9c1a9880425614267832ce437f8ae5f5b69e1f3219f38fc468fc37e48c1919

# Alpine 把发行版 Python 标成 externally-managed，pip 装 uv 需要显式放行。
# 之后一律由 uv 管解释器和虚拟环境，与 app-spark-api 镜像及本地 `uv run` 保持一致。
RUN apk add --no-cache python3 py3-pip \
    && pip install --no-cache-dir --break-system-packages uv==0.10.0

# 关掉 uv 缓存：镜像里的虚拟环境是构建时装好的，运行期只 `uv run --no-sync`，
# 没有要缓存的下载。留着缓存反而会出问题——init Job 以 git 用户运行，而缓存目录
# 默认落在 HOME 下或构建时就被 root 创建，两种情况都不可写。
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1

# README.md 是 pyproject 里声明的 readme，构建 wheel 时必须在场。
WORKDIR /opt/app-spark-forgejo
COPY pyproject.toml uv.lock README.md ./
COPY app_spark_forgejo ./app_spark_forgejo
RUN uv sync --frozen --no-dev

# 还原基础镜像的工作目录，Forgejo 的 entrypoint 和 s6 在这里启动。
# 调 CLI 的一方用 `uv run --directory /opt/app-spark-forgejo --no-sync` 指定项目。
WORKDIR /
