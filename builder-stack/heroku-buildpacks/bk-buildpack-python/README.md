# Blueking Buildpack: Python

蓝鲸 SaaS 应用（Python 语言）构建工具, 基于 [heroku-buildpack-python](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-python).

# 项目结构
```bash
.
├── buildpack      -- heroku-buildpack-python
├── hooks          -- 钩子脚本
├── patchs         -- 修改补丁
├── tests          -- 基于 bats 的脚本测试
├── integration    -- 基于 `bk-saas-pack` 的集成测试
├── Makefile       -- make 命令集
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

# 开发指引
尽量不修改原构建工具中的内容, 而是使用 hook 的方式在原脚本中埋点修改, 或者使用 patch 的方式非侵入式地修改原脚本。
> **引入新的 hook 或 patch 后, 请维护下列的文件说明**

## 已有 hook
- setup-user-compile-hook: 兼容 pre-compile/post-compile
- setup-utils: 从蓝鲸源中下载 stdlib.sh
- pre-install: 安装 python 前的 hook
- post-install: 安装 python 后的 hook

## 已有 patch
- collectstatic.patch: 替换 heroku 的开发文档地址
- python.patch: 替换 heroku 的开发文档地址
- pip-install.patch: 实现使用 pip-tools 安装依赖的功能

## 校验 hook 脚本

如果本机已安装 `shellcheck`, 可直接执行 `make lint` 进行校验。

如果本机未安装 `shellcheck`, 可执行 `make lint-in-container` 在容器内进行校验。

## 本地调试

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

## 从 heroku S3 下载构建依赖

本项目使用 `paas-devops` 工具从 S3 下载构建依赖, 可通过以下方式安装:

```bash
❯ pip install paas-devops
```

### 下载 common 目录

common 目录存储着与 PIP 相关的文件, 可使用以下方式进行下载

```bash
paas-devops download-from-s3 https://heroku-buildpack-python.s3.us-east-1.amazonaws.com -p "common/*"
```

### 下载 heroku-18 目录

heroku-18 目录存储着与安装 Python 相关的文件, 可使用以下方式进行下载

```bash
paas-devops download-from-s3 https://heroku-buildpack-python.s3.us-east-1.amazonaws.com -p "heroku-18/runtimes/*"
```

# 特性开关

python buildpack 可通过环境变量开启部分特性

- `DISABLE_COLLECTSTATIC`: 禁用 `django` 收集静态文件的步骤
- `PIP_VERSION`: 指定需要安装的 `pip` 版本
- `PIP_INDEX_URL`: 设置 index-url
- `PIP_EXTRA_INDEX_URL`: 设置 extra-index-url
- `PIP_INDEX_HOST`: 设置 `trusted-host`
- `STRICT_PIP_MODE`: 使用 `pip-tools` 锁定依赖
- `PIP_TOOLS_VERSION`: 指定需要安装的 `pip-tools` 版本, 不指定将根据 `pip` 和 `python` 版本进行探测
