# svc-redis

`svc-redis` 是蓝鲸开发者中心的 Redis 增强服务模块。Redis 服务实例由 [Redis-Operator](https://github.com/OT-CONTAINER-KIT/redis-operator) 管理生命周期。

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
❯ pip install poetry==2.1.1
❯ poetry install
```

完成依赖安装后，可以使用 poetry 启动项目，常用命令包括：

- `poetry run {COMMAND}`：在 virtualenv 中执行命令。

### 3. 配置本地环境变量

设置环境变量（可以在项目根目录新建 `.envrc` 文件，或在终端中手动执行以下内容）：

```bash
# 与 apiserver 模块通信的密钥
export PAAS_SERVICE_JWT_CLIENTS_KEY="xxx"

# 数据库配置
export MYSQL_NAME="svc_redis"
export MYSQL_USER="root"
export MYSQL_PASSWORD=""
export MYSQL_HOST=""
export MYSQL_PORT="3306"

# 数据库加密密钥，设置后不能变更，否则已加密的 DB 数据将无法解密
# tr -dc A-Za-z0-9 </dev/urandom | head -c 32 | base64
export BKKRILL_ENCRYPT_SECRET_KEY="请参考上面的命令生成"
# Django Settings
export DJANGO_SETTINGS_MODULE="svc_redis.settings"
```

### 4. 集群部署 Redis-Operator

使用以下命令在集群内部署 Redis-Operator：

```bash
# Add the helm chart
$ helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/

# Deploy the redis-operator（已验证 v0.19.3 版本可用）
$ helm upgrade redis-operator ot-helm/redis-operator \
  --install --create-namespace --namespace ot-operators
  
# Test
$ helm test redis-operator --namespace ot-operators 
```


### 5. 初始化数据

运行以下命令初始化数据库：

```bash
python manage.py migrate
```

初始化增强服务的套餐信息：

```python
python manage.py shell

import json
from paas_service.models import Service
from paas_service.models import Plan
from svc_redis.cluster.models import Cluster

# category 为增强服务分类，apiserver 侧也需要参考 apiserver/paasng/fixtures/services.yaml 初始化增强服务分类
svc = Service.objects.create(name="paas_redis", display_name_zh_cn="PaaS-Redis", display_name_en="PaaS-Redis", category=1, logo="http://example.com", available_languages="python,golang,nodejs")

# 创建集群
cluster = Cluster.objects.create(
    name="redis-cluster",
    type="normal",
    description="测试集群",
    ca_data="",
    cert_data="",
    key_data="",
)

config = {
    # Redis 部署架构类型
    # - "Redis": 单节点模式，适用于开发测试环境
    # - "RedisReplication": 主从复制模式，提供基础高可用，适合生产环境
    "type": "RedisReplication",
    # Redis 版本号
    "redis_version": "v7.0.15",
    # Kubernetes 集群名称
    "cluster_name": "redis-cluster",
    # 每个 Redis 实例的内存限制
    "memory_size": "2Gi",
    # 服务暴露方式 (必填)
    # - "ClusterDNS": 通过集群内 DNS 访问服务
    # - "TencentCLB": 通过腾讯云负载均衡器暴露服务
    "service_export_type": "TencentCLB",
    # 是否启用持久化存储
    # True 时会自动创建 PVC，需要集群已配置 StorageClass
    "persistent_storage": False,
    # 是否启用监控
    # 依赖条件：
    # - 集群已安装 Prometheus Operator
    "monitor": False  # 当前未启用监控
}

Plan.objects.create(name="default-redis", description="redis 实例", is_active=True, service_id=svc.uuid, properties={}, config=json.dumps(config))
```

**说明**：apiserver 侧也需要参考 apiserver/paasng/fixtures/services.yaml 初始化增强服务分类

### 6. 启动项目

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
  - name: paas_redis
    endpoint_url: http://localhost:8005/ # 增强服务的访问地址
    provision_params_tmpl:
      engine_app_name: "{engine_app.name}"
    jwt_auth_conf:
      iss: paas-v3
      key: xxx # 与增强服务中配置的 PAAS_SERVICE_JWT_CLIENTS_KEY 的值一致
```

**注意**：仅需修改 `endpoint_url` 和 `key` 的值，其他值无需更改。
