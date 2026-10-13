# apiserver 接入 KMS：信封配置说明

apiserver 启动时可从 KMS 信封读取敏感配置，替代原来以明文写在 values / 环境变量中的密码、密钥和 Token。本文供运维对照现有 values 编写信封内容。

## 开关与挂载

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `PAAS_PLATFORM_KMS_ENABLED` | 是否从信封加载，仅 `true` / `True` 视为开启 | 不开启 |
| `PAAS_PLATFORM_KMS_ENVELOPE_PATH` | 信封文件路径（Base64 文本） | `/etc/kms/envelope` |
| `PAAS_PLATFORM_KMS_PRIVATE_KEY_PATH` | 私钥文件路径（Base64 文本） | `/etc/kms/privateKey` |

ESO 将 `envelope`、`privateKey` 同步为 K8s Secret 并以文件方式挂载到上述路径。开启后，信封不可读或解密失败时进程直接启动失败，不会退回明文配置。

## 信封明文结构

信封解密后是一个 JSON 对象，包含以下几部分，每部分都可以省略：

- `env`：原来通过环境变量提供的敏感配置，**键就是原环境变量名（含 `PAAS_` / `PAAS_WL_` 前缀），值和原来写在环境变量里的内容一模一样**，直接从 values 渲染出的环境变量里复制过来即可。
- `mysql` / `redis` / `rabbitmq` / `bkrepo`：按“类型.实例.字段”分层的账号密码。和 `env` 中的同类配置同时提供时，以分层部分为准。

完整示例（按需删减）：

```json
{
  "env": {
    "PAAS_BK_APP_SECRET": "<应用 Secret>",
    "PAAS_BKKRILL_ENCRYPT_SECRET_KEY": "<加密密钥>",
    "PAAS_ONE_SIMPLE_JWT_AUTH_KEY": "<JWT 密钥>",
    "PAAS_HEALTHZ_TOKEN": "<healthz token>",
    "PAAS_SENTRY_CONFIG": "{dsn='<sentry dsn>'}",
    "PAAS_METRIC_CLIENT_TOKEN_DICT": "{bkmonitor='<监控 token>'}",
    "PAAS_OTEL_BK_DATA_TOKEN": "<trace 上报 token>",
    "PAAS_ELASTICSEARCH_HOSTS": "[{host='es.example.com', port='9200', http_auth='elastic:<ES 密码>'}]",
    "PAAS_SMART_DOCKER_PASSWORD": "<S-Mart 镜像仓库密码>",
    "PAAS_APP_DOCKER_PASSWORD": "<应用镜像仓库密码>",
    "PAAS_WL_AGENT_SANDBOX_ROUTER_AUTH_TOKEN": "<沙箱路由 token>"
  },
  "mysql": {
    "default": {"username": "bkpaas3", "password": "<密码>"},
    "workloads": {"username": "bkpaas3", "password": "<密码>"},
    "legacy": {"username": "open_paas", "password": "<密码>"},
    "console": {"username": "open_paas", "password": "<密码>"}
  },
  "redis": {
    "default": {"password": "<Redis 密码>"},
    "sentinel": {"password": "<Sentinel 密码>"}
  },
  "rabbitmq": {
    "default": {"username": "bkpaas3", "password": "<RabbitMQ 密码>"}
  },
  "bkrepo": {
    "default": {"username": "bkpaas3", "password": "<bkrepo 密码>"}
  }
}
```

## values 对照表

### env 部分

`env` 的值必须保持和原环境变量完全相同的格式，例如 `PAAS_SENTRY_CONFIG` 要写成 `{dsn='...'}`，不能只写 DSN。

| 现有 values 路径 | 信封键 |
|---|---|
| `global.appSecret` | `env.PAAS_BK_APP_SECRET` |
| `global.bkKrillEncryptSecretKey` | `env.PAAS_BKKRILL_ENCRYPT_SECRET_KEY` |
| `global.paasServicesJwtClientKey` | `env.PAAS_ONE_SIMPLE_JWT_AUTH_KEY` |
| `global.healthzToken` | `env.PAAS_HEALTHZ_TOKEN` |
| `global.trace.otlp.token` | `env.PAAS_OTEL_BK_DATA_TOKEN` |
| `apiserver.sentryDsn` | `env.PAAS_SENTRY_CONFIG`，值为 `{dsn='<sentryDsn>'}` |
| `apiserver.serviceMonitor.userToken` | `env.PAAS_METRIC_CLIENT_TOKEN_DICT`，值为 `{bkmonitor='<userToken>'}` |
| `apiserver.elasticSearch.hosts` | `env.PAAS_ELASTICSEARCH_HOSTS`，整串原样复制（密码在 `http_auth` 中） |
| `apiserver.extraEnvs` 等自定义环境变量中的敏感项 | `env.<原环境变量名>`，如 `PAAS_SMART_DOCKER_PASSWORD`、`PAAS_IAM_APP_SECRET` |

只有带前缀的环境变量会生效：apiserver 的配置用 `PAAS_` 前缀，workloads 的配置用 `PAAS_WL_` 前缀。没带前缀的键（如 `AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN`）会被忽略，并在日志中告警。

### 账号密码部分

| 现有 values 路径 | 信封键 | 对应环境变量 |
|---|---|---|
| `apiserver.externalDatabase.default.{user,password}` | `mysql.default.{username,password}` | `PAAS_DATABASE_USER/PASSWORD` |
| `apiserver.externalDatabase.workloads.{user,password}` | `mysql.workloads.{username,password}` | `PAAS_WL_DATABASE_USER/PASSWORD` |
| 自定义的 `PAAS_PAAS_LEGACY_DATABASE_*` | `mysql.legacy.{username,password}` | `PAAS_PAAS_LEGACY_DATABASE_*` |
| `apiserver.externalDatabase.openPaaS.{user,password}` | `mysql.console.{username,password}` | `PAAS_BK_CONSOLE_DATABASE_USER/PASSWORD` |
| `apiserver.externalRedis.default.password` | `redis.default.password` | `PAAS_REDIS_URL`，以及 Redis 类型的 `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` |
| `apiserver.externalRedis.default.sentinel.password` | `redis.sentinel.password` | `PAAS_SENTINEL_PASSWORD`、`PAAS_CELERY_*_SENTINEL_PASSWORD` |
| `apiserver.celeryBrokerUrl` 为 amqp 时的账号密码 | `rabbitmq.default.{username,password}` | amqp 类型的 `CELERY_BROKER_URL` |
| `global.bkrepoConfig.{bkpaas3Username,bkpaas3Password}` | `bkrepo.default.{username,password}` | `PAAS_BLOBSTORE_BKREPO_CONFIG` 中的 `USERNAME` / `PASSWORD` |

说明：

- 只需要在信封里放账号密码，主机、端口、库名仍由原配置提供。只有原配置里有该实例的 `*_DATABASE_NAME` 时，对应的 `mysql.<实例>` 才会生效。
- `mysql.<实例>` 中的 `username`、`password` 都必填，缺一个就启动报错。
- Redis / RabbitMQ 的连接串仍由原配置提供，可以不带密码；信封中的凭证会原样填入连接串，覆盖其中原有的账号密码。因此这些凭证**不能包含 `/`、`?`、`#` 以及 `%XX` 形式的内容**，RabbitMQ 用户名不能包含 `:`，否则启动报错。
- 开启 KMS 后，不能再使用旧的加密连接串环境变量（`DATABASE_URL`、`WL_DATABASE_URL`、`PAAS_LEGACY_DATABASE_URL`），否则启动报错。请改用拆分的 `*_DATABASE_*` 配置加信封中的 `mysql` 部分。

## 未迁移的明文：告警而不阻断

信封里没有、但原配置中仍有明文的敏感配置照常生效，同时输出告警，日志中只包含配置项名：

```
Sensitive setting ELASTICSEARCH_HOSTS is not provided by KMS, using its plaintext config
```

上线后可以按这条告警逐项补齐信封。`ELASTICSEARCH_HOSTS`、`PYTHON_BUILDPACK_PIP_INDEX_URL` 只在其中确实带有账号密码时才告警。

信封补齐后，values 中的明文仍会被 chart 渲染进 ConfigMap / Secret，需要配合 chart 改造（第三步）才能把明文从 values 中去掉。

## 暂不覆盖的范围

以下内容不经过 apiserver 的 settings 加载，本次不处理：

- `apiserver.serviceMonitor.userToken` 渲染进 ServiceMonitor 的 `user_token`：它在 Prometheus 侧使用，不经过 apiserver。
- `initialCluster.tokenValue` / `keyData`（`PAAS_WL_CLUSTER_TOKEN_VALUE` / `PAAS_WL_CLUSTER_KEY_DATA`）：只在初始化集群的 Job 中直接读取环境变量，并写入数据库。
- `init_bkrepo` Job 中的 `BKREPO_PASSWORD`，以及 `ADDONS_` / `LESSCODE_` / `ADMIN_BKREPO_*` 等 apiserver 未使用的环境变量。
- 已写入数据库的凭证，例如集群日志 ES 配置（`ClusterElasticSearchConfig.password`）、源码仓库 OAuth 配置。这些在数据库中已由 `BKKRILL_ENCRYPT_SECRET_KEY` 加密。
