# apiserver 接入 KMS：信封配置说明

apiserver 启动时可从 KMS 信封读取敏感配置，替代原来以明文写在 values / 环境变量中的密码、密钥和 Token。
部署约定遵循 helm-charts 大仓的 KMS 规范，与 bk-apigateway 一致；信封字段与运维的 `bk_paas_runtime_config` 凭证一致。

## 部署约定

| 输入 | 说明 |
|---|---|
| 环境变量 `ENABLE_KMS` | 仅 `true` / `True` 视为开启，其他值或未设置均不开启 |
| 环境变量 `BK_PAAS_KMS_PRIVATE_KEY` | 私钥内容，取自 KMS 凭证的 `private_key` 属性 |
| 文件 `/etc/secrets/bk-paas-kms` | 信封内容，取自 KMS 凭证的 `envelope` 属性 |

开启后，私钥或信封不可用、解密失败时进程直接启动失败，不会退回明文配置。错误信息中不包含凭证内容。
本地开发可以用环境变量 `BK_PAAS_KMS_ENVELOPE_PATH` 指定其他信封路径。

使用 bkpaas3 chart 部署时，只需配置 `apiserver.kms`，以上注入由 chart 完成：

```yaml
apiserver:
  kms:
    enabled: true
    server: "https://kms.example.com"
    role: "default.scope.blueking.secret.bk_paas_runtime_config"
    credential: "default/scope/blueking/secret/bk_paas_runtime_config"
    tls:
      existingSecret: "bk-paas-kms-tls"   # 与 release 同一命名空间
      certCAFilename: "ca.pem"
      # 启用 mTLS 时同时填写
      certFilename: ""
      certKeyFilename: ""
```

chart 会创建 SecretStore、ExternalSecret，生成 `<release>-apiserver-kms-secret`，并注入 apiserver 镜像的所有容器（web、worker、各 Job 和 CronJob）。init 容器和其他组件不注入。SecretStore 使用 apiserver 的 ServiceAccount，不能是 `default`。

环境变量和 `subPath` 文件不会随 Secret 更新而刷新，apiserver 也只在启动时解密一次，凭证轮转后需要重建 Pod。

## 信封字段

信封解密后是一个 JSON 对象，按“凭证类型.实例.字段”分层。apiserver 只读取下表中的字段，其他字段忽略，因此可以与其他组件共用一份凭证。

| 信封字段 | 对应配置 | 运维声明中的取值来源 |
|---|---|---|
| `bkapp_id_secret.default.app_code/app_secret` | `BK_APP_CODE` / `BK_APP_SECRET` | `global.appCode` / `global.appSecret` |
| `mysql.apiserver.username/password` | `DATABASE_USER/PASSWORD` | `apiserver.externalDatabase.default.user/password` |
| `mysql.workloads.username/password` | `WL_DATABASE_USER/PASSWORD` | `apiserver.externalDatabase.workloads.user/password` |
| `mysql.open_paas.username/password` | `BK_CONSOLE_DATABASE_*`、`PAAS_LEGACY_DATABASE_*` | `apiserver.externalDatabase.openPaaS.user/password` |
| `redis.default.password` | 填入 `REDIS_URL`，以及 Redis 类型的 `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `apiserver.externalRedis.default.auth.password` |
| `redis.sentinel.password` | `SENTINEL_PASSWORD`、`CELERY_*_SENTINEL_PASSWORD` | `apiserver.externalRedis.default.sentinel.password` |
| `celery.default.uri` | `CELERY_BROKER_URL`，整串原样使用 | `apiserver.celeryBrokerUrl` |
| `bkrepo.default.username/password` | `BLOBSTORE_BKREPO_CONFIG` 中的 `USERNAME` / `PASSWORD` | `global.bkrepoConfig.bkpaas3Username/bkpaas3Password` |
| `registry.external.username/password` | `SMART_DOCKER_PASSWORD` / `APP_DOCKER_PASSWORD` | `global.externalSmartAppConfig.dockerUsername/dockerPassword` |
| `jwt.services.client_key` | `ONE_SIMPLE_JWT_AUTH_KEY` | `global.paasServicesJwtClientKey` |
| `encryption.bk_krill.secret_key` | `BKKRILL_ENCRYPT_SECRET_KEY` | `global.bkKrillEncryptSecretKey` |
| `encryption.slug.secret_key` | `SLUG_ENCRYPT_SECRET_KEY` | chart 中的硬编码值，见下文 |
| `tokens.healthz.token` | `HEALTHZ_TOKEN` | `global.healthzToken` |
| `tokens.metrics.token` | `METRIC_CLIENT_TOKEN_DICT` 中的 `bkmonitor` | `apiserver.serviceMonitor.userToken` |
| `telemetry.default.token` | `OTEL_BK_DATA_TOKEN` | `global.trace.otlp.token` |
| `sentry.default.dsn` | `SENTRY_CONFIG` 中的 `dsn` | `apiserver.sentryDsn` |
| `elasticsearch.default.hosts` | `ELASTICSEARCH_HOSTS`，按环境变量的规则解析 | `apiserver.elasticSearch.hosts` |

以下字段运维的声明中暂时没有，需要补充（对应 X01“环境扩展”）：

| 信封字段 | 对应配置 | 取值来源 |
|---|---|---|
| `tokens.agent_sandbox_router.token` | workloads 的 `AGENT_SANDBOX_ROUTER_AUTH_TOKEN` | `apiserver.agentSandboxRouterAuthToken` |
| `tokens.agent_sandbox_daemon.token` | `AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN` | `apiserver.env` 中的 `PAAS_AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN` |
| `jwt.paas_analysis.key` | `PAAS_ANALYSIS_JWT_CONF` 中的 `key` | `apiserver.env` 中 `PAAS_PAAS_ANALYSIS_JWT_CONF` 的 `key` |

取值规则：

- 字段缺失或为空字符串时视为未提供，apiserver 保持原有配置来源。字段存在但不是字符串时启动报错。
- 只需要在信封里放账号密码，主机、端口、库名仍由原配置提供。只有原配置里有该实例的 `*_DATABASE_NAME` 时，对应的 `mysql.<实例>` 才会生效；`username` 为空时保留原用户名。
- `METRIC_CLIENT_TOKEN_DICT`、`SENTRY_CONFIG`、`PAAS_ANALYSIS_JWT_CONF` 只替换其中的单个字段，其余字段保持原配置。
- `elasticsearch.default.hosts` 是原来写在环境变量 `PAAS_ELASTICSEARCH_HOSTS` 中的整个字符串。chart 使用 `hostConfig` 数组时，该环境变量的值是 `@json [...]`，信封中也要保存同样的字符串。
- 镜像仓库密码按原配置中的用户名（`SMART_DOCKER_USERNAME` / `APP_DOCKER_USERNAME`）从 `registry.external` 和 `bkrepo.default` 中选出用户名一致的一组。chart 未启用外部镜像仓库时使用 bkrepo 账号，因此不需要额外字段。
- 提供 `celery.default.uri` 时，`CELERY_BROKER_URL` 整串使用信封中的值；未提供且 broker 为 Redis 时，填入 `redis.default.password`。
- `redis.default.password` 会原样填入连接串，覆盖其中原有的密码，因此**不能包含 `/`、`?`、`#` 以及 `%XX` 形式的内容**，否则启动报错。
- 开启 KMS 后，不能再使用旧的加密连接串环境变量（`DATABASE_URL`、`WL_DATABASE_URL`、`PAAS_LEGACY_DATABASE_URL`），否则启动报错。
- `encryption.slug.secret_key` 在 chart 中是写死的 `PAAS_SLUG_ENCRYPT_SECRET_KEY`，信封中必须填同一个值，不能单独更换。

## 对运维凭证声明的修改建议

用 5 套现网 values 渲染运维的声明（只取 apiserver 读取的部分）并加载 apiserver，发现：

- 声明直接写 `{{ .Values.bk_paas.a.b.c }}`，中间某一层不存在时渲染失败。例如没有配置 Sentinel 时，`apiserver.externalRedis.default.sentinel.password` 会报空指针，5 套环境都渲染不出来。应改为 `{{ dig "apiserver" "externalRedis" "default" "sentinel" "password" "" .Values.bk_paas }}`。
- 字符串直接拼进双引号中，值里含有 `"`、`\` 或换行时 JSON 会损坏。应改为 `{{ dig ... | toJson }}` 并去掉外层引号。
- 补充上一节列出的三个字段，`encryption.slug.secret_key` 填 chart 中的值。

按以上方式修正后，5 套环境下开启 KMS 时 apiserver 的生效配置与不开启时一致，把环境变量中出现在信封里的密钥全部清空后也一致。

## 未迁移的明文：告警而不阻断

信封里没有、但原配置中仍有明文的敏感配置照常生效，同时输出告警，日志中只包含配置项名：

```
Sensitive setting ELASTICSEARCH_HOSTS is not provided by KMS, using its plaintext config
```

上线后可以按这条告警逐项补齐信封。`ELASTICSEARCH_HOSTS`、`SENTRY_CONFIG`、`METRIC_CLIENT_TOKEN_DICT` 等只在其中确实带有凭证时才告警。
`apiserver.serviceMonitor.userToken` 未配置时，chart 使用公开的默认值 `your-metric-user-token`，此时会出现 `METRIC_CLIENT_TOKEN_DICT` 告警，建议在 KMS 和 values 中改为随机值。

## 清空 values 中的明文

信封补齐、apiserver 正常启动后，可以把只有 apiserver 使用的明文从 chart 部署用的 values 中清空：

- `global.healthzToken`、`global.trace.otlp.token`、`apiserver.sentryDsn`、`apiserver.agentSandboxRouterAuthToken`
- `apiserver.externalDatabase.{default,workloads,openPaaS}.password`
- `apiserver.externalRedis.default.auth.password`、`apiserver.externalRedis.default.sentinel.password`
- `apiserver.elasticSearch.hosts` / `hostConfig[*].http_auth`
- `apiserver.celeryBrokerUrl` 中的账号密码
- `apiserver.env` 中的 `PAAS_AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN`、`PAAS_PAAS_ANALYSIS_JWT_CONF` 的 `key`
- `global.bkrepoConfig.bkpaas3Password`：清空后 chart 会渲染默认值 `blueking`，被信封覆盖；同时须将 `global.bkrepoConfig.initEnabled` 设为 `false`，避免初始化任务用默认密码创建账号

注意：运维的凭证声明从 `.Values.bk_paas` 取值。清空的只能是 chart 部署用的 values，声明的取值来源必须保留真实值，否则重新渲染声明会把信封中的对应字段也变成空。

以下明文还被其他组件使用，暂时不能清空：

- `global.appSecret`、`global.bkKrillEncryptSecretKey`、`global.paasServicesJwtClientKey`：svc-mysql、svc-rabbitmq、svc-bkrepo、svc-otel 也在使用。
- `apiserver.serviceMonitor.userToken`：同时渲染进 ServiceMonitor，供 Prometheus 采集使用。
- 使用内置 `redis` / `mariadb` / `rabbitmq` 时的 `auth.password`：这些子 chart 本身依赖它。

## 暂不覆盖的范围

以下内容不经过 apiserver 的 settings 加载，本次不处理：

- `initialCluster.tokenValue` / `keyData`（对应 `kubernetes.default.*`）：只在初始化集群的 Job 中直接读取环境变量，并写入数据库。集群初始化完成后可关闭 `initialCluster.enabled` 并清空。
- `init_bkrepo` 的命令行密码参数及 `init-bkrepo` Job 的 `BKREPO_PASSWORD`，以及 `ADDONS_` / `LESSCODE_` / `ADMIN_BKREPO_*` 等 apiserver 未使用的环境变量（对应 `bkrepo.addons/lesscode/admin`）。
- 已写入数据库的凭证，例如集群日志 ES 配置（`ClusterElasticSearchConfig.password`）、源码仓库 OAuth 配置。这些在数据库中已由 `BKKRILL_ENCRYPT_SECRET_KEY` 加密。
