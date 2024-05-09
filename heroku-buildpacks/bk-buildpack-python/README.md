# Blueking Buildpack: Python

蓝鲸 SaaS 应用（Python 语言）构建工具, 基于 [heroku-buildpack-python](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-python).

## 项目结构

```bash
.
├── buildpack      -- heroku-buildpack-python
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
   - TODO: **hooks/setup-utils 当前未被实际安装，待确认后启用**
- patch（补丁）：存放在 patches 目录中， 基于打补丁的方式修改原脚本

> **增加新文件后, 请维护以下文件说明**

### 已有 hook
- setup-user-compile-hook: 兼容 pre-compile/post-compile
- setup-utils: 从蓝鲸源中下载 stdlib.sh
- pre-install: 安装 python 前的 hook
- post-install: 安装 python 后的 hook

### 已有 patch
- collectstatic.patch: 替换 heroku 的开发文档地址
- python.patch: 替换 heroku 的开发文档地址
- pip-install.patch: 实现使用 pip-tools 安装依赖的功能

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
- `PIP_VERSION`: 指定需要安装的 `pip` 版本
- `PIP_INDEX_URL`: 设置 index-url
- `PIP_EXTRA_INDEX_URL`: 设置 extra-index-url
- `PIP_INDEX_HOST`: 设置 `trusted-host`
- `STRICT_PIP_MODE`: 使用 `pip-tools` 锁定依赖
- `PIP_TOOLS_VERSION`: 指定需要安装的 `pip-tools` 版本, 不指定将根据 `pip` 和 `python` 版本进行探测
