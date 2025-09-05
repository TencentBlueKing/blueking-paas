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

1. 安装 Python 3.11

我们推荐使用 [pyenv](https://github.com/pyenv/pyenv) 管理本地的 python 环境

- 依照 [相关指引](https://github.com/pyenv/pyenv#getting-pyenv) 安装 pyenv

- 使用 pyenv 安装 Python 3.11

```shell
❯ pyenv install 3.11.10
```

2. 安装项目依赖

本项目使用 [poetry](https://python-poetry.org/) 管理项目依赖。

- 安装 poetry && 使用 poetry 安装依赖

```shell
❯ make init-py-dep
```

#### poetry 常用命令：

- `poetry env info --path`：获取虚拟环境路径
- `source $(poetry env info --path)/bin/activate`：手动激活虚拟环境
- `python manage.py runserver 0.0.0.0:8000`：在虚拟环境下启动项目，并支持外部访问
- `poetry run {COMMAND}`：使用 virtualenv 执行命令

注：poetry 较新的版本中默认不带 `poetry shell`，需要手动安装

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

收集静态资源之前，需要在 `apiserver/paasng/` 目录下新建 `public/static` 文件夹，用于存放静态资源。可以使用以下命令创建该文件夹：

```shell
❯ mkdir -p apiserver/paasng/public/static
❯ make collectstatic
```

### 完善本地配置

本项目使用 dynaconf 加载用户配置, 可参考 [配置模板](./paasng/conf.yaml.tpl) 创建你的本地配置,
详细的配置说明请阅读 [配置文件](./paasng/paasng/settings/__init__.py)。

具体步骤参考：
1. 在 `apiserver/paasng/` 目录下新建 `settings_local.yaml` 文件，用于配置本地服务（如 MySQL、Redis 等）
2. 在 `apiserver/paasng/` 目录下新建 `settings_files` 目录，用于存放配置通用资源的文件，具体可以参考 [配置模板](./paasng/conf.yaml.tpl) 和 [配置文件](./paasng/paasng/settings/__init__.py)
3. `settings_local.yaml` 中配置 MySQL：
```yaml
DATABASE_HOST: ''
DATABASE_NAME: bk_paas_ng
DATABASE_PASSWORD: ''
DATABASE_PORT: 3306
DATABASE_USER: root
```
4. `apiserver/paasng/settings_files` 中配置通用资源：
```
BKKRILL_ENCRYPT_SECRET_KEY: ''
LOGIN_FULL: ''
BKAUTH_USER_INFO_APIGW_URL: ''
```

### 数据库迁移

```shell
# 假设你当前在 apiserver 项目的根目录下
❯ cd paasng
❯ python manage.py migrate --no-input
❯ python manage.py migrate --no-input --database workloads
```

### 启动服务

- 启动 web 服务

```shell
❯ make server
```

web 服务启动后需要配置本地 hosts 文件，将 web 的 ip 映射到特定的域名，
比如 `app.example.com`，之后浏览器访问 `app.example.com:8000/admin42` 
即可访问到本地蓝鲸 PaaS Admin 控制台

- 启动 celery 后台服务

```shell
❯ make celery
```


## 测试

项目的自动化测试基于 [pytest](https://docs.pytest.org/en/stable/) 框架编写，所有测试用例，可被笼统分为单元测试、API 测试和 E2E 测试三类。

#### 单元测试

单元测试是项目中数量最多的测试用例类型，它们主要位于 [./paasng/tests](./paasng/tests) 目录下。单元测试数量众多，也最为全面，它们覆盖了项目绝大部分功能场景。

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

#### API 测试

API 测试，指通过请求接口并验证响应是否符合预期的自动化测试。同单元测试相比，API 测试的速度通常更慢、依赖项更多，但是能覆盖更多的业务逻辑。

本项目的 API 测试代码主要位于 [./paasng/tests/api/](./paasng/tests/api/) 目录下。与传统的“黑盒 API 测试”（发送真实 HTTP 请求）有所不同，本项目的 API 测试是基于 Django/DRF 框架的 API 测试套件编写，并不发出真实网络请求，不过，这并不影响最终的测试效果。

一个典型的 API 测试，由“数据准备”、“发送请求”、“验证响应”这三个步骤组成。为了提升测试效果，让代码尽可能地便于维护，编码时请遵循以下建议：

- 用例代码尽可能地简单，避免复杂逻辑；
- 尽量只通过调用 API 来完成测试；
- 减少依赖项，尽量避免 Mock，不直接操作数据模型；
- 除 bk_app 等 fixture 之外，不轻易引入其他模块代码；
- 避免直接调用各模块的功能函数（可以通过调 API 替代）；
- 使用 `reverse()` 函数获取请求路径，而不是硬编码字符串。

示例代码可参考：[./paasng/tests/api/bkapp_model/test_network_config.py](./paasng/tests/api/bkapp_model/test_network_config.py)。

#### E2E 测试

E2E 测试是“端对端（End-to-end）测试”的缩写，特指那些需要访问真实的依赖服务才能正常运行的测试。E2E 测试运行速度慢，成本相比单元测试要高许多，比方说，运行测试前，你需要准备一个真实可用的 Kubernetes 集群（通常用 [kind](https://github.com/kubernetes-sigs/kind) 启动）。

当前，E2E 测试用例的数量不多，主要覆盖的场景包括：

- ingress：验证在不同版本 Kubernetes 集群、不同版本的 Ingress-Nginx 路由下，请求应用时，请求路径与关键头信息能被正常处理。

E2E 测试代码位于 [./paasng/tests/paas_wl/e2e](./paasng/tests/paas_wl/e2e) 目录中，也是基于 pytest 框架编写。执行这些测试前，必须额外提供以下配置项：

```yaml
FOR_TEST_E2E_INGRESS_CONFIG:
  NGINX_NODE_IP: "127.0.0.1"
  NGINX_HTTP_PORT: 80
  NGINX_HTTPS_PORT: 443
```

相比单元测试，运行 E2E 测试需提供额外的命令行参数 `--run-e2e-test`，示例：

```bash
$ pytest --run-e2e-test --reuse-db -s ./tests/paas_wl/e2e
```

更多详细信息，可参考文档 [./paasng/tests/paas_wl/e2e/ingress/README.md](./paasng/tests/paas_wl/e2e/ingress/README.md)。


#### 网关 API 测试

为了让用户能够使用 access_token 访问注册在 API 网关上的用户态 API，开发者中心增加了以下配置：

- `apigw_manager.apigw.authentication.ApiGatewayJWTUserMiddleware` 中间件
- `bkpaas_auth.backends.APIGatewayAuthBackend` 身份认证

在 `apigw-manager` 和 `bkpaas-auth` 这两个 SDK 的升级后，需要验证 JWT 认证的有效性，以确保 API 网关能够正确地处理认证请求。

**步骤 1: 使用 access_token 访问 API 网关获取合法的 JWT**

参考如下命令访问 API 网关上的 API，并添加调试参数：`-H 'X-BKAPI-Debug: True' -H 'X-BKAPI-Dynamic-Debug: True'`，在响应头中查找`x-bkapi-jwt`，记录该值用于下一步测试。

```bash
curl -X GET \
-H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***", "access_token": "您的 access_token"}' \
-d '{}' \
--insecure https://paasv3.apigw.example.com/prod/bkapps/applications/lists/minimal \
-H 'X-BKAPI-Debug: True' \
-H 'X-BKAPI-Dynamic-Debug: True' \
-vv
```

**步骤 2: 使用 JWT 访问本地或测试环境的用户态 API**

使用上一步获取到 JWT 访问本地或者测试环境任意用户态 API。

```bash
curl -X GET \
"http://dev.example.com:8001/api/accounts/feature_flags/" \
-H "x-bkapi-jwt: 上一个步骤获取到的 x-bkapi-jwt"
```

发布到测试环境和正式环境后，可以直接使用 access_token 调用 API 网关上的用户态 API，验证其是否能够正常响应。


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
import Vue from "vue";

window.Vue = Vue;
```

否则, `Django Template` 将无法直接使用 Nodejs 中的组件。

#### Template 页面开发指引

Template 页面开发模式与常规的 Django 项目无异, 但是使用了 [Vuejs](https://cn.vuejs.org/)
和 [MagicBox Vue 组件库](https://magicbox.bk.tencent.com/static_api/v3/components_vue/2.0/example/index.html#/)
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

### admin42 页面 403 问题

需要进入数据库执行以下命令

```sql
UPDATE `bk_paas_ng`.`accounts_userprofile` SET `role` = 4 WHERE `id` = 1;
```

该命令修改指定 id 的用户为超级用户

### bkpaas_iam_migration 数据库迁移失败问题

如果在进行数据库迁移的过程中出现 bkpaas_iam_migration 迁移无法完成的情况，可以在配置文件中添加配置：`BK_IAM_SKIP: true`，
然后重新执行迁移命令

### apiserver 运行起来但无法访问 PaaS Admin 问题

查看控制台，如果提示缺失 APIGW，需要在配置文件中增加 `BKAUTH_USER_INFO_APIGW_URL: ""`

### 执行报错 NoSuchBucket, 找不到 Bucket

结合配置文件, 检查对象存储 (如 Minio) 是否创建好了以下 Bucket:

- BLOBSTORE_BUCKET_APP_SOURCE, 默认为 `bkpaas3-slug-packages`
- BLOBSTORE_BUCKET_TEMPLATES, 默认为 `bkpaas3-apps-tmpls`
- BLOBSTORE_BUCKET_AP_PACKAGES, 默认为 `bkpaas3-source-packages`