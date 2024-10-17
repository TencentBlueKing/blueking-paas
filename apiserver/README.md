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

我们推荐使用 [nvm](https://github.com/nvm-sh/nvm) 管理本地的 nodejs 环境
- 依照 [相关指引](https://github.com/nvm-sh/nvm#installing-and-updating) 安装 nvm
- 使用 nvm 安装 nodejs 14

```shell
❯ nvm install 14 
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

项目的自动化测试通过 pytest 编写的测试用例编写，这些测试用例，可被笼统分为单元测试和 E2E 测试两类。

#### 单元测试

单元测试是项目中数量最多的测试用例类型，它们主要位于 <./paasng/tests> 目录下。单元测试数量多，也最为全面，它们覆盖了项目绝大部分功能场景。

本地开发时，可以执行 pytest 来运行测试用例：

```bash
# 假设你当前处于 paasng 目录下，设置好有效的项目配置文件。
$ export DJANGO_SETTINGS_MODULE=paasng.settings
$ pytest --reuse-db -s --maxfail=1 ./tests/
```

参数说明：

- `--reuse-db`：每次启动测试时尝试复用测试数据库，能提高执行速度
- `--maxfail=1`：最多允许一个失败用例
- `-s`：打印标准输出

你可以访问 [pytest 的官方文档](https://docs.pytest.org/en/stable/) 来了解更多。

> 提示：每次提交代码改动前，请务必保证通过所有单元测试。

#### E2E 测试

E2E 测试是“端对端（End-to-end）测试”的缩写，特指那些需要访问真实的依赖服务才能正常运行的测试。E2E 测试运行速度慢，成本相比单元测试要高许多，比方说，运行 E2E 测试前，你需要准备一个真实可用的 Kubernetes 集群（通常用 [kind](https://github.com/kubernetes-sigs/kind) 启动）。

当前，E2E 测试用例的数量不多，主要覆盖的场景包括：

- 验证在不同版本 Kubernetes 集群、不同版本的 Ingress-Nginx 路由下，请求应用时，请求路径与关键头信息能被正常处理。

E2E 测试代码位于 <./paasng/tests/paas_wl/e2e> 目录中，也是基于 pytest 框架编写。执行 E2E 测试前，必须提供以下配置项：

```yaml
FOR_TEST_E2E_INGRESS_CONFIG:
  NGINX_NODE_IP: "127.0.0.1"
  NGINX_HTTP_PORT: 80
  NGINX_HTTPS_PORT: 443
```

执行 E2E 测试需传递特定的命令行参数 `--run-e2e-test`，如：

```bash
$ pytest --run-e2e-test --reuse-db -s ./tests/paas_wl/e2e
```

更多详细信息，可参考文档 <./paasng/tests/paas_wl/e2e/README.md>。

## 数据库迁移

```shell
# 假设你当前在 apiserver 项目的根目录下
❯ cd paasng
❯ python manage.py migrate --no-input
❯ python manage.py migrate --no-input --database workloads
```

## 启动服务

- 启动 web 服务

```shell
❯ make server
```

- 启动 celery 后台服务

```shell
❯ make celery
```

## 常见开发场景

### 开发管理端功能

本项目管理端（Admin42）使用 Vue 开发, 代码分为两部分:

- Nodejs 组件: 由 nodejs 管理的纯 js 组件, 构建后以 bundle 形式被 Template 加载,
  项目路径位于 `apiserver/paasng/assets`
- Template 页面: 基于 Django Template 服务端渲染的 html 页面,
  项目路径位于 `apiserver/paasng/paasng/plat_admin/admin42/`

#### Nodejs 组件开发指引

Nodejs 组件开发模式与常规的 Nodejs 项目无异, 但为了更方便地与 Django Template 集成,
本项目未使用任何 `JavaScript 模块化技术`, 即所有组件都需要自行往 `window` 对象挂载, 例如:

```javascript
import Vue from 'vue'

window.Vue = Vue
```

否则, `Django Template` 将无法直接使用 Nodejs 中的组件。

#### Template 页面开发指引

Template 页面开发模式与常规的 Django 项目无异, 但是使用了 [Vuejs](https://cn.vuejs.org/)
和 [MagicBox Vue组件库](https://magicbox.bk.tencent.com/static_api/v3/components_vue/2.0/example/index.html#/)
完成前端的功能开发。

在开发新的 Template 模板时应该遵循以下规范:

1. 使用 MagicBox Vue 组件完成前端页面开发
2. 首屏数据使用服务端渲染至 HTML, 以简化前后端交互的逻辑
3. 避免硬编码后端接口, 使用 `url` 标签动态获取接口地址
4. 监听 `DOMContentLoaded` 事件完成 Vue 对象的初始化

### 开发系统 API

“系统 API”指那些提供给其他后台系统使用，而非给普通用户访问的功能性 API。调用这类 API 时，请求发起方无需提供用户登录态，只要携带有效的蓝鲸应用身份（AppID/AppSecret）即可。

系统 API 的工作原理为：

- API 被设定为必须拥有系统级权限才能访问，比如 `SYSAPI_READ_APPLICATIONS` 代表系统级的读取蓝鲸应用信息的权限；
- 平台预设了一批系统级角色，它们拥有系统级权限，比如 `SYSTEM_API_BASIC_READER`（系统 API 基础可读者）角色拥有 `SYSAPI_READ_SERVICES` 和 `SYSAPI_READ_APPLICATIONS` 权限；
- 系统级角色无法绑定给普通用户，必须绑定到系统账号上

系统账号是一种特殊账号，目前支持两种管理和认证方式：

1. 基于 `private_token` 认证：由管理员在 PaaS Admin 中手动添加账号并分配 token，使用方携带该 token 完成请求
2. 基于蓝鲸 API 网关应用认证：使用方首先在蓝鲸 API 网关上申请 PaaS 网关的对应系统 API 权限，之后在请求对应 API 时，平台将自动创建一个对应的系统账号，完成请求

这两种方式各有优缺点。第一种方式，操作略为繁琐，需人工手动维护账号，且 private_token 的引入在一定程度上增加了安全风险。第二种方式操作简便，但对 API 网关的应用认证体系依赖性非常强，假如某个系统 API 在网关上的权限配置不当（如允许任意应用访问），则可能产生滥用风险。

#### 代码示例

代码层面上，系统 API 和普通 API 的主要区别体现在视图层。下面是一份代码示例：

```python
@ForceAllowAuthedApp.mark_view_set
class SysBkPluginLogsViewset(viewsets.ViewSet):

    # 该接口已注册到 APIGW
    # 网关名称 list_bk_plugin_logs
    # 请勿随意修改该接口协议
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request, code):
        """查询某个蓝鲸插件的结构化日志"""
        # 常见逻辑为完成一些和“当前用户”无关的系统级查询或管理能力
```

要点如下：

1. 使用 `@ForceAllowAuthedApp.mark_view_set` 装饰视图类后，如果请求携带了经认证的有效应用身份（经由 API 网关完成认证与权限校验），平台将自动创建一个角色为 `SYSTEM_API_BASIC_READER` 的系统账号，由它完成请求。
    - 后续如需要调整该账号的角色，可在 PaaS Admin 中完成。
2. 使用 `@site_perm_required` 装饰视图函数，以保证请求只允许那些拥有系统级权限的账号访问（**非常重要，因为系统 API 一般都是用户无关，极容易发生越权问题。**）

## FAQ

### docker compose 安装 bundle 依赖问题

如果在安装 docker 时, 安装了 docker-compose-plugin, 需要修改'blueking-paas/apiserver/dev_utils/bundle/start.sh' 中的 docker-compose 改为 docker compose

### poetry install 时 hash 值对不上问题 

先执行

```shell
poetry config experimental.new-installer false
```

再重新执行 poetry install 即可

### admin42 页面 403 问题

需要进入数据库执行以下命令

```sql
UPDATE `bk_paas_ng`.`accounts_userprofile` SET `role` = 4 WHERE `id` = 1;
```

该命令修改指定 id 的用户为超级用户
