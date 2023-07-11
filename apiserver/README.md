# apiserver

apiserver 为 blueking-paas 项目的主控模块。

## 本地开发指引

### 准备依赖环境

本地开发时依赖的一些服务，可使用 `docker-compose` 快速启动。

- [安装 Docker](https://docs.docker.com/engine/install/)
- [安装 Docker Compose](https://docs.docker.com/compose/install/)

确保本地环境已安装好 `docker` 和 `docker-compose` 后, 参考以下指令即可启动并初始化 `MySQL / Redis / Minio` 等依赖服务。

相关服务的配置，请参考 `blueking-paas/apiserver/dev_utils/bundle/README.md`

```shell
# 假设你当前在 apiserver 项目的根目录下
❯ cd dev_utils/bundle

# 参考 dev_utils/bundle/README.md，完成 .env 文件的初始化
❯ echo "..." > .env

# 利用 docker 启动依赖环境
❯ ./start.sh
```

### 准备 Python 开发环境

1. 安装 Python 3.8

我们推荐使用 [pyenv](https://github.com/pyenv/pyenv) 管理本地的 python 环境

- 依照 [相关指引](https://github.com/pyenv/pyenv#getting-pyenv) 安装 pyenv

- 使用 pyenv 安装 Python 3.8

```shell
❯ pyenv install 3.8.13
```

- 使用 virtualenv 工具，为项目初始化独立的运行环境

```shell
virtualenv -p ~/.pyenv/versions/3.8.13/bin/python3 bkpaas-venv
source ./bkpaas-venv/bin/active
```

2. 安装项目依赖

本项目使用 [poetry](https://python-poetry.org/) 管理项目依赖。

- 安装 poetry && 使用 poetry 安装依赖

```shell
❯ make init-py-dep
```

完成依赖安装后，便可以使用 poetry 启动项目了，常用命令：

- `poetry shell`：进入当前的 virtualenv
- `poetry run {COMMAND}`：使用 virtualenv 执行命令

### (可选) 准备 Nodejs 开发环境

apiserver 项目的管理端（Admin42）使用 Nodejs 进行开发, 如需开发管理端功能, 需要准备 Nodejs 开发环境

1. 安装 [Nodejs](https://github.com/nodejs)，推荐使用 v14.21.1 版本

```shell
❯ brew install node@14 
```

2. 安装项目依赖

管理端项目使用 [npm](https://www.npmjs.com/) 管理项目依赖。

```shell
❯ make init-node-dep
```

3. 打包构建前端项目

```shell
❯ make npm-build
```

4. 收集静态资源

```shell
❯ make collectstatic
```

## 完善本地配置

本项目使用 dynaconf 加载用户配置, 可参考 [配置模板](./paasng/conf.yaml.tpl) 创建你的本地配置,
详细的配置说明请阅读 [配置文件](./paasng/paasng/settings/__init__.py)。

## 测试

本项目的所有单元测试均基于 pytest, 请务必保证单元测试通过后再提交代码。

```shell
❯ make test
```

- `--reuse-db` 表示在每次启动测试时尝试复用测试数据库
- `-s` 表示打印标准输出

## 启动服务

- 启动 web 服务

```shell
❯ make server
```

- 启动 celery 后台服务

```shell
❯ make celery
```

## 开发管理端功能

本项目管理端（Admin42）使用 Vue 开发, 代码分为两部分:

- Nodejs 组件: 由 nodejs 管理的纯 js 组件, 构建后以 bundle 形式被 Template 加载,
  项目路径位于 `apiserver/paasng/assets`
- Template 页面: 基于 Django Template 服务端渲染的 html 页面,
  项目路径位于 `apiserver/paasng/paasng/plat_admin/admin42/`

### Nodejs 组件开发指引

Nodejs 组件开发模式与常规的 Nodejs 项目无异, 但为了更方便地与 Django Template 集成,
本项目未使用任何 `JavaScript 模块化技术`, 即所有组件都需要自行往 `window` 对象挂载, 例如:

```javascript
import Vue from 'vue'

window.Vue = Vue
```

否则, `Django Template` 将无法直接使用 Nodejs 中的组件。

### Template 页面开发指引

Template 页面开发模式与常规的 Django 项目无异, 但是使用了 [Vuejs](https://cn.vuejs.org/)
和 [MagicBox Vue组件库](https://magicbox.bk.tencent.com/static_api/v3/components_vue/2.0/example/index.html#/)
完成前端的功能开发。

在开发新的 Template 模板时应该遵循以下规范:

1. 使用 MagicBox Vue 组件完成前端页面开发
2. 首屏数据使用服务端渲染至 HTML, 以简化前后端交互的逻辑
3. 避免硬编码后端接口, 使用 `url` 标签动态获取接口地址
4. 监听 `DOMContentLoaded` 事件完成 Vue 对象的初始化
