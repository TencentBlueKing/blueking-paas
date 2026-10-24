# Blueking Buildpack: Python

蓝鲸 SaaS 应用（Python 语言）构建工具, 基于 [heroku-buildpack-python](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-python).

## 项目结构

```bash
.
├── buildpack      -- heroku-buildpack-python
├── docs           -- 使用说明
├── hooks          -- 钩子脚本
├── patches        -- 修改补丁
├── tests          -- 基于 bats 的脚本测试
├── integration    -- 基于 `bk-saas-pack` 的集成测试
├── Makefile       -- make 命令集
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

## 开发指引

为尽量降低维护成本，推荐不修改原 buildpack 文件, 而是使用 hook 和 patch 的方式来调整 buildpack 行为：

- hook（钩子）：存放在 hooks 目录中，是独立的 Bash 脚本，在 buildpack 的不同阶段被显式调用
- patch（补丁）：存放在 patches 目录中， 基于打补丁的方式修改原脚本

> **增加新文件后, 请维护以下文件说明**

### 已有 hook
- setup-user-compile-hook: 兼容 pre-compile/post-compile
- pre-install: 安装 python 前的 hook
- post-install: 安装 python 后的 hook
- pre-install-dependencies: 安装应用依赖前，把 uv.lock 中来自公网 PyPI 的包改为从 PIP_INDEX_URL 指向的镜像下载（改写逻辑见 uv-lock-mirror.awk）
- post-install-dependencies: 安装应用依赖后，还原 uv.lock

### 已有 patch
- bin/compile.patch: 埋点 hook（setup-user-compile-hook、pre-install、post-install、pre-install-dependencies、post-install-dependencies），并加载 apt buildpack 导出的环境变量
- lib/python.sh.patch: 设置了 BUILDPACK_S3_BASE_URL 时，从该目录下载 Python 运行时（上游 v302 起不再支持这个变量）
- lib/uv.sh.patch: 设置了 BUILDPACK_S3_BASE_URL 时，从同一目录下载 uv，文件名为 `uv-<版本>-<arch>-unknown-linux-gnu.tar.gz`
- lib/pip.sh.patch、lib/poetry.sh.patch、lib/pipenv.sh.patch: 安装 pip / Poetry / Pipenv 时保留上游的 `--isolated`，并显式传入 PIP_INDEX_URL（及 PIP_INDEX_HOST），从内部 PyPI 镜像下载

包管理器（pip、Pipenv、Poetry、uv）的支持情况和使用方式见 [docs/package-managers.md](docs/package-managers.md)。

### 校验 hook 脚本

如果本机已安装 `shellcheck`, 可直接执行 `make lint` 进行校验。

如果本机未安装 `shellcheck`, 可执行 `make lint-in-container` 在容器内进行校验。

### 单元测试

首先执行 `make patch` 将 hooks 和 patches 补丁文件应用到官方 buildpack 中，然后执行 `make test` 运行所有单元测试。

### 本地调试

1. 调试时, 可执行 `make pack version=${version}` 将构建工具打包成 tarball
2. 使用 `bk-saas-pack` 测试构建

```bash
❯ bk-saas-pack debug --help
NAME:
   bk-saas-pack debug - 启动调试容器

USAGE:
   bk-saas-pack debug [command options] [arguments...]

OPTIONS:
   --node-buildpack value    Node 构建工具的路径(未压缩的 tarball), 不指定会使用镜像中的默认值
   --python-buildpack value  Python 构建工具的路径(未压缩的 tarball), 不指定会使用镜像中的默认值
   --src value               Application Source Dir
```

## 项目发布流程

1. 发布前为项目创建对应的 tag
2. 在蓝盾流水线上执行发布, 将自动归档至蓝盾制品库
3. 修改 PaaS 3.0 引用的构建工具下载链接

## 特性开关

python buildpack 可通过环境变量开启部分特性

- `DISABLE_COLLECTSTATIC`: 禁用 `django` 收集静态文件的步骤
- `BUILDPACK_S3_BASE_URL`: Python 运行时与 uv 的下载目录，不设置时从上游公网地址下载
- `PIP_INDEX_URL`: 设置 index-url
- `PIP_EXTRA_INDEX_URL`: 设置 extra-index-url
- `PIP_INDEX_HOST`: 设置 `trusted-host`
