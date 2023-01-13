# bkpaas workloads configuration file example

## ---------------------------------------- 全局配置 ----------------------------------------

## 用于加密数据库内容的 Secret
# BKKRILL_ENCRYPT_SECRET_KEY: ''

## （Django）特定 Django 安装的密钥。用于提供 加密签名，默认值为：${BKKRILL_ENCRYPT_SECRET_KEY}
## 更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#secret-key
# SECRET_KEY: ''

## （Django）Django Debug 标志，永远不要在 DEBUG 开启的情况下将网站部署到生产环境中
## 更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#debug
# DEBUG: false

## （Django）可以访问 Django 网站可以服务的主机／域名的字符串列表，默认值为 ['*']，表示任意
## 更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#allowed-hosts
# ALLOWED_HOSTS:
#   - '127.0.0.1'


## ---------------------------------------- 数据库，日志与存储配置 ----------------------------------------

## 数据库 Host
# DATABASE_HOST: ''
## 数据库名称
# DATABASE_NAME: bk_engine_ng
## 数据库相关配置
# DATABASE_OPTIONS: {}
## 数据库访问密码
# DATABASE_PASSWORD: ''
## 数据库端口
# DATABASE_PORT: 3306
## 数据库访问 USER
# DATABASE_USER: root

## 日志等级，高于或等于该等级的日志才会被记录
# LOG_LEVEL: INFO

## Redis 日志存储配置，若不配置，则不会向 redis 写日志
# LOGGING_REDIS_HANDLER:
#   class: paas_wl.utils.log.LogstashRedisHandler
#   level: INFO
#   message_type: python-logstash
#   queue_name: enginev3_log_list
#   redis_url: redis://localhost:6379/0
#   tags:
#     - example

## 是否记录代码与数据库互动有关的信息，如请求执行的应用程序级别的 SQL 语句，默认值为 False
# LOGGING_ENABLE_SQL_QUERIES: false


## ---------------------------------------- 运行时默认配置 ----------------------------------------

## 默认 slug 包运行镜像，默认值 bkpaas/slugrunner
# DEFAULT_SLUGRUNNER_IMAGE: bkpaas/slugrunner
## 默认 slug 包构建镜像，默认值 bkpaas/slugbuilder
# DEFAULT_SLUGBUILDER_IMAGE: bkpaas/slugbuilder

## 源码构建用户身份
# BUILDER_USERNAME: blueking
## 构建 Python 应用时，强制使用该地址覆盖 PYPI Server 地址
# PYTHON_BUILDPACK_PIP_INDEX_URL: ''
## 从源码构建应用时，额外注入的环境变量
# BUILD_EXTRA_ENV_VARS: {}


## ---------------------------------------- 对象存储配置 ----------------------------------------

## 对象存储类型，可选值为 s3，bkrepo，一旦指定则会强制使用对应的配置
## 若没有指定或为空，且 BLOBSTORE_BKREPO_CONFIG 不为空值，则使用 bkrepo
## 若指定为 s3，则必须配置 BLOBSTORE_S3_ENDPOINT，BLOBSTORE_S3_ACCESS_KEY，BLOBSTORE_S3_SECRET_KEY 项
# BLOBSTORE_TYPE: bkrepo

## S3 服务地址，默认值 http://127.0.0.1:9100
# BLOBSTORE_S3_ENDPOINT: ''
## S3 访问用户名，默认值为 minio
# BLOBSTORE_S3_ACCESS_KEY: ''
## S3 访问密钥
# BLOBSTORE_S3_SECRET_KEY: ''
## 应用构建 SLUG 存放 bucket 名，默认无需修改
## 注意应和 apiserver 中 BLOBSTORE_BUCKET_APP_SOURCE 保持一致
# BLOBSTORE_S3_BUCKET_NAME: bkpaas3-slug-packages

## S3 服务地域，默认值 us-east-1，一般无需修改
# BLOBSTORE_S3_REGION_NAME: us-east-1
## S3 签名版本，默认值 s3v4，一般无需修改
# BLOBSTORE_S3_SIG_VERSION: s3v4

## 对象存储（bkrepo）配置
# BLOBSTORE_BKREPO_CONFIG:
#   PROJECT: bkpaas
#   ENDPOINT: http://bkrepo.example.com
#   USERNAME: bkpaas3
#   PASSWORD: ''


## ---------------------------------------- 服务导出配置 ----------------------------------------

## 默认容器内监听地址，默认 5000
# CONTAINER_PORT: 5000

## 服务相关插件配置
# SERVICES_PLUGINS: {}


## ---------------------------------------- Redis 配置 ----------------------------------------

## 与 apiserver 通信的 redis 管道, 需要确保两个项目中的配置一致
# STREAM_CHANNEL_REDIS_URL: redis://localhost:6379/0
## 用于保存缓存等其他数据的 redis 服务器地址，未配置时使用 STREAM_CHANNEL_REDIS_URL 的值
# REDIS_URL: redis://localhost:6379/0
## Redis Sentinel master name
# SENTINEL_MASTER_NAME: ''
## Redis Sentinel 密码(非 Redis 实例密码)
# SENTINEL_PASSWORD: ''

## Redis 连接配置，可自定义设置 timeout，keepalive 等
# REDIS_CONNECTION_OPTIONS:
#   socket_timeout: 3
#   socket_connect_timeout: 3
#   socket_keepalive: true
#   socket_keepalive_options: {}


## ---------------------------------------- Celery 配置 ----------------------------------------

## （Celery） Celery 队列 URL，默认值 amqp://
# CELERY_BROKER_URL: ''

##（Celery）Celery 任务执行结果存储 URL
# CELERY_RESULT_BACKEND: ''

## celery 队列相关配置，如果没有设置，且队列类型为 Redis，将会被赋予 REDIS_CONNECTION_OPTIONS 的值
# CELERY_BROKER_TRANSPORT_OPTIONS: {}

## （Celery）Celery 任务默认队列，默认值为 celery
# CELERY_TASK_DEFAULT_QUEUE: celery


## ---------------------------------------- 资源限制配置 ----------------------------------------

## Web 模块默认副本数量，默认值：{'stag': 1, 'prod': 2}
# DEFAULT_WEB_REPLICAS_MAP:
#   stag: 1
#   prod: 2

## 构建 slug 包资源规格，按 k8s 资源配额格式书写
# SLUGBUILDER_RESOURCES_SPEC:
#   limits:
#     cpu: 2000m
#     memory: 4096Mi
#   requests:
#     cpu: 500m
#     memory: 1024Mi


## ---------------------------------------- 鉴权配置 ----------------------------------------

## 具体枚举值参考 bkpaas_auth ProviderType 类
# USER_TYPE: 3

## 用户身份校验类型，默认值为 bk_token
# BKAUTH_BACKEND_TYPE: bk_token
## 用于获取 Token 的 App Code
# BKAUTH_TOKEN_APP_CODE: ''
## 用于获取 Token App Secret
# BKAUTH_TOKEN_SECRET_KEY: ''

## 统一登陆域名
# BKAUTH_BK_LOGIN_DOMAIN: ''
## 统一登陆 API Path（需与 BKAUTH_BK_LOGIN_DOMAIN 配合使用）
# BKAUTH_BK_LOGIN_PATH: ''

## paasv3 apiserver 服务地址
# PAAS_APISERVER_ENDPOINT: http://localhost:8080

# 用于服务间鉴权的 JWT key，该配置可替代 INTERNAL_SERVICES_JWT_AUTH_CONF 和 PAAS_SERVICE_JWT_CLIENTS
# 当 PaaS 的所有服务都使用同一个 JWT key 时，可使用该配置项。
# ONE_SIMPLE_JWT_AUTH_KEY: ''
## 调用 PAAS 服务 jwt 配置，支持使用 ONE_SIMPLE_JWT_AUTH_KEY 简化配置
# PAAS_SERVICE_JWT_CLIENTS:
#   - iss: paas-v3
#     key: ''
## 调用内部服务（如：workloads） jwt 配置，支持使用 ONE_SIMPLE_JWT_AUTH_KEY 简化配置
# INTERNAL_SERVICES_JWT_AUTH_CONF:
#   iss: paas-v3
#   key: ''

## ---------------------------------------- 部署环境相关 ----------------------------------------

## 系统注入环境变量统一前缀，默认值为 BKPAAS_，一般不需要修改
# SYSTEM_CONFIG_VARS_KEY_PREFIX: BKPAAS_

## （兼容）应用日志存储卷名称，默认为 applogs
# VOLUME_NAME_APP_LOGGING: applogs
## （兼容）应用日志写入路径，默认为
# VOLUME_MOUNT_APP_LOGGING_DIR: /app/logs
## （兼容）应用日志挂载到 Host 的路径，默认为 /tmp/logs
# VOLUME_HOST_PATH_APP_LOGGING_DIR: /tmp/logs


## 多模块应用日志存储卷名称，默认为 appv3logs
# MUL_MODULE_VOLUME_NAME_APP_LOGGING: appv3logs
## 多模块应用日志写入路径，默认为 /app/v3logs
# MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR: /app/v3logs
## 多模块应用日志挂载到 Host 的路径，默认为 /tmp/v3logs
# MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR: /tmp/v3logs


## ---------------------------------------- 调度集群相关 ----------------------------------------

## 指定 kubectl 使用的 config.yaml 文件路径，容器化交付时由 secret 挂载而来
## 默认值：/data/kubelet/conf/kubeconfig.yaml
# KUBE_CONFIG_FILE: /data/kubelet/conf/kubeconfig.yaml


## ---------------------------------------- 监控数据配置 ----------------------------------------

## 指标服务相关 Token 配置
# METRIC_CLIENT_TOKEN_DICT:
#   bkmonitor: example-metric-client-token

## 调用 Healthz API 需要的 Token
# HEALTHZ_TOKEN: example-healthz-token

## 是否支持蓝鲸监控（下发 ServiceMonitor 的总开关）
# BKMONITOR_ENABLED: false
## 蓝鲸监控运维相关的额外配置
# BKMONITOR_METRIC_RELABELINGS: []
## 能否通过 APIGW 访问蓝鲸监控 API，要求该环境已注册
# ENABLE_BK_MONITOR_APIGW: true
## 蓝鲸监控网关环境：测试 stage、正式 prod
# BK_MONITOR_APIGW_SERVICE_STAGE: stage

## ---------------------------------------- 多区域配置 ----------------------------------------

## 所有应用版本名字，用于初始化默认进程配置信息等，默认值为 ['default']
# ALL_REGIONS:
#   - default


## ---------------------------------------- Ingress 配置 ----------------------------------------

## 不指定则使用默认，可以指定为 bk-ingress-nginx
# APP_INGRESS_CLASS: ''

## ingress extensions/v1beta1 资源路径是否保留末尾斜杠，默认值为 true
# APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH: true

## 是否开启“现代” Ingress 资源的支持，将产生以下影响
## - 支持使用 networking.k8s.io/v1 版本的 Ingress 资源
## - （**重要**）对于 K8S >= 1.22 版本的集群, 必须开启该选项。因为这些集群只能使用 networking.k8s.io/v1 版本的 Ingress 资源
## - （**重要**）对于 K8S >= 1.22 版本的集群, 必须使用 >1.0.0 版本的 ingress-nginx
##
## 假如关闭此配置，可能有以下风险：
##  - 只能处理 extensions/v1beta1 和 networking.k8s.io/v1beta1 版本的 Ingress 资源, 如果未来的 Kubernetes 集群版本删除了对该
##    apiVersion 的支持，服务会报错
##  - 只能使用 <1.0 版本的 ingress-nginx
# ENABLE_MODERN_INGRESS_SUPPORT: true

## 应用独立域名相关配置
# CUSTOM_DOMAIN_CONFIG:
  ## 是否允许使用独立域名
  # enabled: true
  ## 允许用户配置的独立域名后缀列表，如果为空列表，允许任意独立域名
  # valid_domain_suffixes: []
  ## 是否允许用户修改独立域名相关配置，如果为 False，只能由管理员通过后台管理界面调整应用独立域名配置
  # allow_user_modifications: true

## 独立域名简化版配置，表示允许用户配置的独立域名后缀列表，为空表示允许任意域名
## CUSTOM_DOMAIN_CONFIG 拥有更高的优先级
# VALID_CUSTOM_DOMAIN_SUFFIXES: []


# -------------------------------------- internal 配置，仅开发项目与特殊环境下使用 --------------------------------------

## 调用 APIGW API 使用的 APP Code，目前用于创建 webconsole
# BK_APP_CODE: ''
## 调用 APIGW API 使用的 APP Secret
# BK_APP_SECRET: ''
## 网关前缀 URL 模板，格式如 http://localhost:8080/api/{api_name}/
# BK_API_URL_TMPL: ''
## 网关所部署的环境
# APIGW_ENVIRONMENT: 'prod'

## Sentry 服务配置，包含 DSN 等，配置示例：{"dsn": "http://example-sentry-dsn"}
# SENTRY_CONFIG: {}

## 是否开启 OTEL 数据上报，默认值为 false
# ENABLE_OTEL_TRACE: false
## 是否记录 DB 相关 tracing
# OTEL_INSTRUMENT_DB_API: True
## 上报数据服务名称，一般不需要修改
# OTEL_SERVICE_NAME: bkpaas3-workloads
## sdk 采样规则（always_on / always_off / parentbased_always_on...）
# OTEL_SAMPLER: always_on
## OTEL 上报到监控平台的数据 Token，可通过监控平台上新建应用获得
# OTEL_BK_DATA_TOKEN: -1
## OTEL 上报地址（grpc）
# OTEL_GRPC_URL: http://localhost:8080

