# svc-mysql

`svc-mysql` 是蓝鲸开发者中心的 MySQL 增强服务模块。

## 本地开发指引

### 1. 安装 Python 3.11

推荐使用 [pyenv](https://github.com/pyenv/pyenv) 管理 Python 环境。

- 安装 pyenv，请参考 [相关指引](https://github.com/pyenv/pyenv#getting-pyenv)。
- 使用 pyenv 安装 Python 3.11：

```shell
❯ pyenv install 3.11.10
```

### 2. 安装项目依赖

本项目使用 [poetry](https://python-poetry.org/) 管理依赖。

- 安装 poetry 并通过它安装依赖：

```shell
❯ make init-py-dep
```

完成依赖安装后，可以使用 poetry 启动项目，常用命令包括：

- `poetry shell`：进入当前 virtualenv。
- `poetry run {COMMAND}`：在 virtualenv 中执行命令。

### 3. 配置本地环境变量

设置环境变量（可以在项目根目录新建 `.envrc` 文件，或在终端中手动执行以下内容）：

```bash
# 与 apiserver 模块通信的密钥
export PAAS_SERVICE_JWT_CLIENTS_KEY="xxx"

# 数据库配置
export MYSQL_NAME="svc_mysql"
export MYSQL_USER="root"
export MYSQL_PASSWORD=""
export MYSQL_HOST=""
export MYSQL_PORT="3306"

# 数据库加密密钥，设置后不能变更，否则已加密的 DB 数据将无法解密
# tr -dc A-Za-z0-9 </dev/urandom | head -c 32 | base64
export BKKRILL_ENCRYPT_SECRET_KEY="请参考上面的命令生成"
# Django Settings
export DJANGO_SETTINGS_MODULE="svc_mysql.settings"
```

### 4. 初始化数据

运行以下命令初始化数据库：

```bash
python manage.py migrate
```

初始化增强服务的套餐信息：

```python
import json
from paas_service.models import Service
from paas_service.models import Plan

# category 为增强服务分类，apiserver 侧也需要参考 apiserver/paasng/fixtures/services.yaml 初始化增强服务分类
svc = Service.objects.create(name="mysql", display_name_zh_cn="MySQL", display_name_en="MySQL", category=1, logo="http://example.com", available_languages="python,golang,nodejs")

# 分配给 SaaS 的数据库实例信息，注意 user 和 password 必须有 root 权限
config = {"auth_ip_list":["%"], "host":"127.0.0.1", "password":"blueking", "port":3006,"user":"root"}

# 注意这里是社区版本的初始化数据，如果是其他版本，需要修改 region 的值
Plan.objects.create(name="default-mysql", description="mysql 实例", is_active=True, service_id=svc.uuid, properties={ "region":"default"}, config=json.dumps(config))
```

**说明**：apiserver 侧也需要参考 apiserver/paasng/fixtures/services.yaml 初始化增强服务分类

### 5. 启动项目

使用以下命令启动项目：

```bash
python manage.py runserver 8005
```

运行项目后，如果终端输出以下信息，说明 apiserver 已成功调用增强服务的 API：

```
[03/Nov/2024 15:03:40] "GET /meta_info/ HTTP/1.1" 200
[03/Nov/2024 15:03:40] "GET /services/ HTTP/1.1" 200
```

apiserver 会定时调用这两个 API，您也可以手动重启 apiserver 主动触发一次调用。

## 与 apiserver 模块通信

增强服务仅提供 API，分配和解绑等操作在 apiserver 侧完成。这两个模块通过 JWT 完成身份校验，因此需要分别配置 JWT KEY。

1. **增强服务侧配置**

在增强服务中设置环境变量：

```bash
export PAAS_SERVICE_JWT_CLIENTS_KEY="xxx"
```

2. **apiserver 侧配置**

在 apiserver 本地配置文件中，将 `SERVICE_REMOTE_ENDPOINTS` 项添加如下内容：

```yaml
SERVICE_REMOTE_ENDPOINTS:
  - name: mysql_remote
    endpoint_url: http://localhost:8005/ # 增强服务的访问地址
    provision_params_tmpl:
      egress_info: "{cluster_info.egress_info_json}"
      engine_app_name: "{engine_app.name}"
      operator: "{engine_app.owner}"
    jwt_auth_conf:
      iss: paas-v3
      key: xxx # 与增强服务中配置的 PAAS_SERVICE_JWT_CLIENTS_KEY 的值一致
```

**注意**：仅需修改 `endpoint_url` 和 `key` 的值，其他值无需更改。

## 如何配置不同规格的增强服务

增强服务允许给套餐设置不同的规格来满足给应用差异化分配增强服务实例的需求。如分别配置 MySQL5.7、MySQL8.0 2 个规格数据库实例，应用申请增强服务的时候可以按需选择。

![img](docs/resource/img/svc_spec.png)

SpecDefinition 用于描述规格的元信息，Specification 表示一个具体的 SpecDefinition 记录对应的值，可绑定到多个 Plan 上。

```python
import json
from paas_service.models import Service
from paas_service.models import SpecDefinition, Specification
from paas_service.models import Plan


# 1.给增强服务添加规格定义
definition = SpecDefinition.objects.create(name="version", display_name_zh_cn="数据库版本", display_name_en="Database version", recommended_value="5.7")
svc = Service.objects.first()
svc.specifications.add(definition)

# 2.给规格赋值
spec_version_57 = Specification.objects.create(value="5.7", display_name_zh_cn="MySQL 5.7",  display_name_en="MySQL 5.7", definition=definition)
spec_version_80 = Specification.objects.create(value="8.0", display_name_zh_cn="MySQL 8.0",  display_name_en="MySQL 8.0", definition=definition)

# 3. 给存量的套餐添加规格信息
for plan in Plan.objects.all():
    plan.specifications.add(spec_version_57)

# 4. 添加新的套餐并设置规格
# 分配给 SaaS 的数据库实例信息，注意 user 和 password 必须有 root 权限
config = {"auth_ip_list":["%"], "host":"127.0.0.2", "password":"blueking", "port":3006,"user":"root"}
# 注意这里是社区版本的初始化数据，如果是其他版本，需要修改 region 的值
plan = Plan.objects.create(name="mysql-8.0", description="mysql 8.0", is_active=True, service_id=svc.uuid, properties={ "region":"default"}, config=json.dumps(config))
# 给套餐添加规格信息
plan.specifications.add(spec_version_80)
```
