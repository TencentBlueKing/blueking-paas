# apiserver

apiserver 项目为 bkpaas 的主控模块。

# 本地开发指引

## 准备依赖环境

本地开发时依赖的一些服务，可使用 `docker-compose` 快速启动。

1. [安装 Docker](https://docs.docker.com/engine/install/)

2. [安装 Docker Compose](https://docs.docker.com/compose/install/)

3. 启动依赖

确保本地环境已安装好 `docker` 和 `docker-compose` 后, 参考以下指令即可启动并初始化 MySQL/Redis/Minio 等依赖服务。相关服务的配置，请参考 `bkpaas/apiserver/dev_utils/bundle/README.md`

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ cd dev_utils/bundle
❯ ./start.sh
```

## 准备 Python 开发环境

1. 安装 Python 3.8

可以使用 [pyenv](https://github.com/pyenv/pyenv) 管理本地的 python 环境

- 依照 [相关指引](https://github.com/pyenv/pyenv#getting-pyenv) 安装 pyenv

- 使用 pyenv 安装 Python 3.8

```bash
❯ pyenv install 3.8.13
```

2. 安装项目依赖

本项目使用 [poetry](https://python-poetry.org/) 管理项目依赖。

- 安装 poetry

```bash
❯ pip install poetry
```

- 使用 poetry 安装依赖

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ poetry install --no-root
```

完成依赖安装后，便可以使用 poetry 启动项目了，常用命令：
- poetry shell：进入当前的 virtualenv
- poetry run {COMMAND}：使用 virtualenv 执行命令

## (可选) 准备 Nodejs 开发环境

apiserver 项目的管理端使用 nodejs 管理依赖, 如需开发管理端功能, 需要准备 Nodejs 开发环境

1. 安装 Nodejs >= 10.10.0 以上

2. 安装项目依赖

管理端项目使用 [npm](https://www.npmjs.com/) 管理项目依赖。

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ npm install
```

3. 打包构建前端项目

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ npm run build
```

4. 收集静态资源

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ python paasng/manage.py collectstatic
```

## 完善本地配置

本项目使用 dynaconf 加载用户配置, 可参考 [配置模板](./paasng/conf.yaml.tpl) 创建你的本地配置, 详细的配置说明请阅读 [配置文件](./paasng/paasng/settings/__init__.py)。

## 测试

本项目的所有单元测试均基于 pytest, 请务必保证单元测试通过后再提交代码。

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ cd paasng
❯ pytest --reuse-db -s --maxfail 1 .
```

- `--reuse-db` 表示在每次启动测试时尝试复用测试数据库
- `-s` 表示打印标准输出

## 启动服务

- 启动 web 服务

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ cd paasng
❯ gunicorn paasng.wsgi -w ${GUNICORN_CONCURRENCY:-8} --timeout ${GUNICORN_TIMEOUT:-150} -b 0.0.0.0:8000 -k gevent --max-requests ${GUNICORN_MAX_REQUESTS:-2048} --access-logfile=- --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" in %(L)s seconds' --log-level ${GUNICORN_LOG_LEVEL:-INFO} --log-file=-
```

- 启动 celery 后台服务

```bash
# 假设你当前在 apiserver 项目的根目录下

❯ cd paasng
❯ celery -A paasng worker -c ${CELERY_CONCURRENCY:-6} -l ${CELERY_LOG_LEVEL:-info}
```

## 开发管理端功能(前端)

本项目管理端(前端)使用 Vue 开发, 代码分为两部分:
- Nodejs 组件: 由 nodejs 管理的纯 js 组件, 构建后以 bundle 形式被 Template 加载, 项目路径位于 `bkpaas/apiserver/paasng/assets`
- Template 页面: 基于 Django Template 服务端渲染的 html 页面, 项目路径位于 `bkpaas/apiserver/paasng/paasng/plat_admin/admin42/`

### Nodejs 组件开发指引

Nodejs 组件开发模式与常规的 Nodejs 项目无异, 但为了更方便地与 Django Template 集成, 本项目未使用任何 `JavaScript 模块化技术` , 因此所有组件都需要自行往 `window` 对象挂载, 例如:

```javascript
import Vue from 'vue'

window.Vue = Vue
```

否则, `Django Template` 将无法直接使用 Nodejs 中的组件。

### Template 页面开发指引

Template 页面开发模式与常规的 Django 项目无异, 但是使用了 [Vuejs](https://cn.vuejs.org/v2/guide/) 和 [MagicBox Vue组件库](https://magicbox.bk.tencent.com/static_api/v3/components_vue/2.0/example/index.html#/) 完成前端的功能开发。

在开发新的 Template 模板时应该遵循以下规范:
1. 使用 MagicBox Vue组件完成前端页面开发
2. 首屏数据使用服务端渲染至 HTML, 以简化前后端交互的逻辑
3. 不硬编码任何后端接口, 使用 `url` 标签动态获取接口地址
4. 监听 DOMContentLoaded 事件完成 Vue 对象的初始化
