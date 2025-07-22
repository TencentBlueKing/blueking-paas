# bkpaas apiserver configuration file example

## 用于加密数据库内容的 Secret
# BKKRILL_ENCRYPT_SECRET_KEY: ''

## 选择加密数据库内容的算法，可选值：'SHANGMI', 'CLASSIC'，分别对应 'SM4CTR' 和 'FernetCipher' 算法
# BK_CRYPTO_TYPE : ''

## （Django）特定 Django 安装的密钥。用于提供 加密签名，默认值为：${BKKRILL_ENCRYPT_SECRET_KEY}
## 更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#secret-key
# SECRET_KEY: ''

## （Django）Django Debug 标志，永远不要在 DEBUG 开启的情况下将网站部署到生产环境中
## 更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#debug
# DEBUG: false

## INSTALLED_APPS 扩展内容
# EXTRA_INSTALLED_APPS: []

## 国际化 cookie 默认写在整个蓝鲸的根域下
# BK_COOKIE_DOMAIN: ''

## （Django）更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#static-url
# STATIC_URL: ''

## 日志等级，高于或等于该等级的日志才会被记录
# LOG_LEVEL: INFO

# 用于存放日志文件的目录，默认值为空，表示不使用任何文件，所有日志直接输出到控制台。
# 可配置为有效目录，支持相对或绝对地址，比如："logs" 或 "/var/lib/app_logs/"。
# 配置本选项后，原有的控制台日志输出将关闭。
# LOGGING_DIRECTORY: null

# 日志文件所使用的格式，默认为 json，可选值：json、text
# LOGGING_FILE_FORMAT: "json"

# 是否总是打印日志到控制台，默认为否，仅当配置了日志目录，仍需控制台日志时使用
# LOGGING_ALWAYS_CONSOLE: false

## 是否记录代码与数据库互动有关的信息，如请求执行的应用程序级别的 SQL 语句，默认值为 False
# LOGGING_ENABLE_SQL_QUERIES: false

# 发送通知的渠道，如果没有配置，则仅记录日志并不调用发送通知的 API
BK_CMSI_ENABLED_METHODS: ["send_mail", "send_sms", "send_weixin"]

## ------------------------------------------ Django 基础配置（自定义） ------------------------------------------

## 数据库 Host
# DATABASE_HOST: ''
## 数据库名称
# DATABASE_NAME: bk_paas_ng
## 数据库相关配置
# DATABASE_OPTIONS: {}
## 数据库访问密码
# DATABASE_PASSWORD: ''
## 数据库端口
# DATABASE_PORT: 3306
## 数据库访问 USER
# DATABASE_USER: root

## 注：WL 数据库即为源 workloads 模块数据库，
## 在模块合并后，apiserver 将使用两个数据库（bk_paas_ng, bk_engine_ng）

## 数据库 Host
# WL_DATABASE_HOST: ''
## 数据库名称
# WL_DATABASE_NAME: bk_engine_ng
## 数据库相关配置
# WL_DATABASE_OPTIONS: {}
## 数据库访问密码
# WL_DATABASE_PASSWORD: ''
## 数据库端口
# WL_DATABASE_PORT: 3306
## 数据库访问 USER
# WL_DATABASE_USER: root

## Redis 服务地址
# REDIS_URL: redis://127.0.0.1:6379/0
## Redis Sentinel master name
# SENTINEL_MASTER_NAME: ''
## Redis Sentinel 密码(非 Redis 实例密码)
# SENTINEL_PASSWORD: ''

## 默认 Cache 配置，若无该配置则检查是否配置 Redis，若存在则作为缓存，否则使用临时文件作为缓存
# DEFAULT_CACHE_CONFIG: {}

## （Django）更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#force-script-name
# FORCE_SCRIPT_NAME: ''

## （Django）CSRF 写入 Cookie 域名
## 更多参考：https://docs.djangoproject.com/zh-hans/4.0/ref/settings/#csrf-cookie-domain
# CSRF_COOKIE_DOMAIN: ''

## （Django）更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#session-cookie-domain
# SESSION_COOKIE_DOMAIN: ''

## 可以访问 Django 网站的主机／域名的字符串列表，默认值为 ['*']，表示任意
## 更多参考：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#allowed-hosts
# ALLOWED_HOSTS:
#   - '127.0.0.1'

## （django-cors-headers）CORS 允许的来源列表
## 更多参考：https://github.com/adamchainz/django-cors-headers#cors_allowed_origin_regexes-sequencestr--patternstr
# CORS_ORIGIN_REGEX_WHITELIST: []


## ------------------------------------------ Celery 配置 ------------------------------------------

## （Celery）Celery 队列 URL，默认值 amqp://
## 更多参考：https://docs.celeryq.dev/en/stable/userguide/configuration.html?#broker-url
# CELERY_BROKER_URL: ''
## （Celery）Celery 任务执行结果存储 URL
## 更多参考：https://docs.celeryq.dev/en/stable/userguide/configuration.html?#result-backend
# CELERY_RESULT_BACKEND: ''
##（Celery） Celery 队列心跳检查间隔，单位为秒
## 更多参考：https://docs.celeryq.dev/en/stable/userguide/configuration.html?#broker-heartbeat
# CELERY_BROKER_HEARTBEAT: 120
## （Celery）Celery 队列相关配置，如果没有设置且队列类型为 Redis，将会被赋予 REDIS_CONNECTION_OPTIONS 的值
## 更多参考：https://docs.celeryq.dev/en/stable/userguide/configuration.html?#broker-transport-options
# CELERY_BROKER_TRANSPORT_OPTIONS: {}


## ------------------------------------------ 项目系统类配置 ------------------------------------------

## 调用蓝鲸 API （组件、BkOAuth 服务等）的鉴权信息
# BK_APP_CODE: ''
# BK_APP_SECRET: ''
## PaaS 2.0 在权限中心注册的系统ID （并非是平台的 Code）
# IAM_SYSTEM_ID: bk_paas
## PaaS 3.0 在权限中心注册的系统 ID
# IAM_PAAS_V3_SYSTEM_ID: bk_paas3
## 请求权限中心的 App Code，默认值与 BK_APP_CODE 相同
# IAM_APP_CODE: ''
## 请求权限中心的 App Secret，默认值与 BK_APP_SECRET 相同
# IAM_APP_SECRET: ''
## 是否通过网关访问 IAM，默认值为 True
# BK_IAM_USE_APIGATEWAY: true
## Auth 服务默认 PROVIDER 类型
# BKAUTH_DEFAULT_PROVIDER_TYPE: BK
## 跳过初始化已有应用数据到权限中心
# BK_IAM_SKIP: false

## 是否启用多租户模式，本配置项仅支持在初次部署时配置，部署后不支持动态调整
# ENABLE_MULTI_TENANT_MODE: false

## 网关访问 IAM 地址
# BK_IAM_APIGATEWAY_URL: ''
## 蓝鲸 ESB 服务地址
# BK_COMPONENT_API_URL: ''
## 蓝鲸的组件 API 地址，网关 SDK 依赖该配置项（该项值与 BK_COMPONENT_API_URL 一致）
# COMPONENT_SYSTEM_HOST: http://localhost:8080
## 蓝鲸的组件 API 测试环境地址
# COMPONENT_SYSTEM_HOST_IN_TEST: http://localhost:8080
## bk-apigateway-inner 网关 API 地址
# BK_APIGATEWAY_INNER_API_URL: http://bkapi.example.com/api/bk-apigateway-inner/prod/
## （Apigw Manager SDK）PaaS 服务 API Gateway 注册网关名称
## 更多参考：https://github.com/TencentBlueKing/bkpaas-python-sdk/tree/master/sdks/apigw-manager
# BK_APIGW_NAME: paasv3
## 网关 API 接口地址模板
## 更多参考：https://github.com/TencentBlueKing/bkpaas-python-sdk/tree/master/sdks/apigw-manager
# BK_API_URL_TMPL: 'http://localhost:8080/api/{api_name}/'
## 开发者中心 region 与 APIGW user_auth_type 的对应关系
# REGION_TO_USER_AUTH_TYPE_MAP: {}
## 指标服务相关 Token 配置
# METRIC_CLIENT_TOKEN_DICT:
#   bkmonitor: example-metric-client-token
## 是否默认允许创建 Smart 应用
# IS_ALLOW_CREATE_SMART_APP_BY_DEFAULT: true
## 使用“应用迁移”功能，迁移到云原生应用时所使用的目标集群名称
# MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER: ""

## 开发者中心使用的 k8s 集群组件（helm chart 名称）
# BKPAAS_K8S_CLUSTER_COMPONENTS:
# - bk-ingress-nginx
# - bkapp-log-collection
# - bkpaas-app-operator
# - bcs-general-pod-autoscaler

## ------------------------------------------ Healthz 配置 ------------------------------------------

## 调用 Healthz API 需要的 Token
# HEALTHZ_TOKEN: example-healthz-token
## 服务健康探针列表
# HEALTHZ_PROBES:
#   - paasng.monitoring.healthz.probes.PlatformMysqlProbe
#   - paasng.monitoring.healthz.probes.WorkloadsMysqlProbe
#   - paasng.monitoring.healthz.probes.PlatformRedisProbe
#   - paasng.monitoring.healthz.probes.ServiceHubProbe
#   - paasng.monitoring.healthz.probes.PlatformBlobStoreProbe
#   - paasng.monitoring.healthz.probes.BKIAMProbe

## 蓝鲸的组件 API 的 Healthz 地址
# COMPONENT_SYSTEM_HEALTHZ_URL: ''
## API Gateway Healthz 地址
# APIGW_HEALTHZ_URL: http://localhost:8080


## ------------------------------------------ 平台基础功能配置 ------------------------------------------

## 是否自动创建用户，默认打开，关闭后新用户将无法访问
# AUTO_CREATE_REGULAR_USER: true

## 每个应用下最多创建的模块数量
# MAX_MODULES_COUNT_PER_APPLICATION: 10
## 应用单个模块下最多创建的 process 数量
# MAX_PROCESSES_PER_MODULE: 8

## 旧版本 PaaS 数据库 Host
# PAAS_LEGACY_DATABASE_HOST: ''
## 旧版本 PaaS 数据库名称
# PAAS_LEGACY_DATABASE_NAME: tencent_paas
## 旧版本 PaaS 数据库相关配置
# PAAS_LEGACY_DATABASE_OPTIONS: {}
## 旧版本 PaaS 数据库访问密码
# PAAS_LEGACY_DATABASE_PASSWORD: ''
## 旧版本 PaaS 数据库端口
# PAAS_LEGACY_DATABASE_PORT: 3306
## 旧版本 PaaS 数据库访问 USER
# PAAS_LEGACY_DATABASE_USER: root

## 旧版本 PaaS 数据库，敏感字段所使用的加密 key
# PAAS_LEGACY_DB_ENCRYPT_KEY: ''


## ------------------------------------------ 对象储存配置 ------------------------------------------

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
## S3 服务地域，默认值 us-east-1，一般无需修改
# BLOBSTORE_S3_REGION_NAME: us-east-1
## S3 签名版本，默认值 s3v4，一般无需修改
# BLOBSTORE_S3_SIG_VERSION: s3v4

## Logo 图片存储地址
# RGW_ENDPOINT_URL: ''
## Logo 图片存储用户名
# RGW_ACCESS_KEY_ID: ''
## Logo 图片存储密钥
# RGW_SECRET_ACCESS_KEY: ''

## 对象存储（bkrepo）配置
# BLOBSTORE_BKREPO_CONFIG:
#   PROJECT: bkpaas
#   ENDPOINT: http://bkrepo.example.com
#   USERNAME: bkpaas3
#   PASSWORD: ''
## bkrepo 项目名称，仅在创建项目时使用。bkrepo 的项目 ID 在 BLOBSTORE_BKREPO_CONFIG["PROJECT"] 中定义
## NOTE: 按目前 bkrepo 的规则，启用/关闭多租户模式的情况下:
## 关闭多租户: 项目 ID == 项目名称
## 启用多租户: 项目 ID == f"{租户 ID}_{项目名称}"
# BLOBSTORE_BKREPO_PROJECT_NAME = "bkpaas"
## 增强服务 LOGO bucket
# SERVICE_LOGO_BUCKET: bkpaas3-platform-assets
## 应用 Logo 存储 bucket 名称
# APP_LOGO_BUCKET: bkpaas3-apps-logo


## ------------------------------------------ 服务地址配置 ------------------------------------------

## 蓝鲸PaaS平台访问地址，用于平台访问链接拼接与内置环境变量的配置项
# BKPAAS_URL: http://localhost:8080
## 蓝鲸 PaaS2.0 平台访问地址，用于平台访问链接拼接与内置环境变量的配置项
# BK_PAAS2_URL: ''
## 蓝鲸 PaaS2.0 平台内网访问地址，用于内置环境变量的配置项
# BK_PAAS2_INNER_URL: ''

## 蓝鲸应用默认 logo 地址
# APPLICATION_DEFAULT_LOGO: http://localhost:8080/static/images/default_logo.png
## 插件应用默认 Logo 图片地址
# PLUGIN_APP_DEFAULT_LOGO: http://localhost:8080/static/images/plugin_default_logo.png

## SSM 服务地址
# BK_SSM_URL: ''
## 权限中心内网访问地址，用于对接权限中心
# BK_IAM_V3_INNER_URL: ''
## 蓝鲸 CMDB 服务地址
# BK_CC_URL: ''
## 蓝鲸 Job 服务地址
# BK_JOB_URL: ''
## 权限中心服务地址
# BK_IAM_URL: ''
## 蓝鲸用户管理服务地址
# BK_USER_URL: ''
## 蓝鲸监控地址
# BK_MONITORV3_URL: ''
## 蓝鲸日志平台地址
# BK_LOG_URL: ''
## bkrepo 服务地址
# BK_REPO_URL: ''
## 蓝盾服务地址
# BK_CI_URL: ''
## CodeCC 服务地址
# BK_CODECC_URL: ''
## turbo 服务地址
# BK_TURBO_URL: ''
## 蓝盾流水线服务地址
# BK_PIPELINE_URL: ''
## 蓝鲸节点管理平台地址
# BK_NODEMAN_URL: ''
## 蓝鲸容器管理平台地址
# BK_BCS_URL: ''
## 蓝鲸服务配置中心地址
# BK_BSCP_URL: ''
## 蓝鲸审计中心地址
# BK_AUDIT_URL: ''
## 为兼容 PaaS 2.0 而注入的内置环境变量，格式如：{"BK_SOPS_URL": "http://localhost:8080"}
# BK_PAAS2_PLATFORM_ENVS: {}

## 应用移动端访问地址，用于渲染模板与内置环境变量的配置项
# BKPAAS_WEIXIN_URL_MAP:
#   stag: http://localhost:8080/
#   prod: http://localhost:8080/

## 应用移动端允许的域名后缀，如果为空列表，允许任意域名
# MOBILE_DOAMIN_SUFFIXS: []

# 统一登录页面地址，用于模板渲染与内置环境变量的配置项
# LOGIN_FULL: ''
# LOGIN_SIMPLE: ''

## 蓝鲸统一登录服务地址，用于平台登录
# BK_LOGIN_API_URL: ''
## 蓝鲸桌面访问地址，用于内置环境变量
# BK_CONSOLE_URL: ''

## 默认 Region 名称
# DEFAULT_REGION_NAME: default
## Region 配置
# REGION_CONFIGS: {}

## 蓝鲸 OAuth 服务地址
# BK_OAUTH_API_URL: http://localhost:8080


## ------------------------------------ 用户鉴权模块 bkpaas_auth SDK 相关配置 ------------------------------------

## API Gateway 公钥，用于解析通过 API Gateway 的请求，该值为空时跳过解析
# APIGW_PUBLIC_KEY: ''

## 是否启用多租户模式, 需要和 ENABLE_MULTI_TENANT_MODE 保持一致
# BKAUTH_ENABLE_MULTI_TENANT_MODE: ENABLE_MULTI_TENANT_MODE

## 如果当前环境没有 bk-login 网关，则设置 BKAUTH_USER_INFO_APIGW_URL 为空字符串, bkpaas_auth 将使用 BKAUTH_USER_COOKIE_VERIFY_URL
## 如果设置了有效的 BKAUTH_USER_INFO_APIGW_URL, BKAUTH_USER_COOKIE_VERIFY_URL 配置将被忽略, 使用网关进行用户身份校验
## 多租户模式下(BKAUTH_ENABLE_MULTI_TENANT_MODE=True)必须设置有效的 BKAUTH_USER_INFO_APIGW_URL, 否则无法使用租户功能
# BKAUTH_USER_INFO_APIGW_URL = ''

## 用户身份校验类型，默认值为 bk_token
# BKAUTH_BACKEND_TYPE: bk_token
## 用于获取 Token 的 App Code，默认值与 BK_APP_CODE 相同
# BKAUTH_TOKEN_APP_CODE: ''
## 用于获取 Token App Secret，默认值与 BK_APP_SECRET 相同
# BKAUTH_TOKEN_SECRET_KEY: ''
## 验证用户登陆态（是否过期）的地址
# BKAUTH_USER_COOKIE_VERIFY_URL: http://localhost:8080
## 通过 Token 获取用户信息 API
# BKAUTH_TOKEN_USER_INFO_ENDPOINT: http://localhost:8080
## 获取 Token API 地址
# BKAUTH_TOKEN_GRANT_ENDPOINT: http://localhost:8080
## 校验 Token API 地址
# BKAUTH_TOKEN_CHECK_ENDPOINT: http://localhost:8080
## 统一登陆域名
# BKAUTH_BK_LOGIN_DOMAIN: http://localhost:8080
## 统一登陆 API Path（需与 BKAUTH_BK_LOGIN_DOMAIN 配合使用）
# BKAUTH_BK_LOGIN_PATH: /
## 具体枚举值参考 bkpaas_auth ProviderType 类
# USER_TYPE: 3


## ------------------------------------ 云 API 相关配置 ------------------------------------

## 获取应用态的 AccessToken 的 API 地址
# TOKEN_AUTH_ENDPOINT: ''
## 刷新应用态的 AccessToken 的 API 地址
# TOKEN_REFRESH_ENDPOINT: ''
## Auth 服务环境（stag/prod）
# AUTH_ENV_NAME: prod
## 请求 Token 服务所使用的 App Code
# CLI_AUTH_CODE: ''
## 请求 Token 服务所使用的 App Secret
# CLI_AUTH_SECRET: ''


## ------------------------------------ 插件应用相关配置 ------------------------------------
# 是否允许创建蓝鲸插件应用
IS_ALLOW_CREATE_BK_PLUGIN_APP = False

## 管理插件应用的 API 网关环境
# BK_PLUGIN_APIGW_SERVICE_STAGE: prod

## 管理插件应用的 API 网关用户类型
# BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE: default


## ------------------------------------ 源码托管相关配置项 ------------------------------------

## Docker 仓库配置
# DOCKER_REGISTRY_CONFIG:
#   DEFAULT_REGISTRY: https://hub.docker.com
#   ALLOW_THIRD_PARTY_REGISTRY: false


## ------------------------------------ 引擎相关配置项 ------------------------------------

# 用于服务间鉴权的 JWT key，该配置可替代 PAAS_SERVICE_JWT_CLIENTS
# 当 PaaS 的所有服务都使用同一个 JWT key 时，可使用该配置项。
# ONE_SIMPLE_JWT_AUTH_KEY: ''

## 环境变量保留前缀列表
# CONFIGVAR_PROTECTED_PREFIXES: ["BKPAAS_", "KUBERNETES_"]

## 调用 PAAS 服务 JWT 配置，支持使用 ONE_SIMPLE_JWT_AUTH_KEY 简化配置
# PAAS_SERVICE_JWT_CLIENTS:
#   - iss: paas-v3
#     key: ''

## 保存应用源码包、初始化代码 Bucket 名称
# BLOBSTORE_BUCKET_APP_SOURCE: bkpaas3-slug-packages
## 保存应用模板代码 Bucket 名称
# BLOBSTORE_BUCKET_TEMPLATES: bkpaas3-apps-tmpls
## 存储源码包 Bucket 名称
# BLOBSTORE_BUCKET_AP_PACKAGES: bkpaas3-source-packages

## S-Mart 应用默认增强服务配置信息
# SMART_APP_DEFAULT_SERVICES_CONFIG:
#   mysql: {}

## 针对 slug 环境对敏感信息加密密钥
# SLUG_ENCRYPT_SECRET_KEY: ''

## 默认运行时镜像名称
# DEFAULT_RUNTIME_IMAGES:
#   default: blueking


## ------------------------------------ 增强服务相关 ------------------------------------

## 各本地增强服务 vendor 基础配置
# SERVICES_VENDOR_CONFIGS: {}

## 是否禁用定时任务调度器
# DISABLE_PERIODICAL_JOBS: false

## 远程增强服务配置，支持简配的三类模板（mysql，bkrepo，rabbitmq）
## 配置项：
## - SERVICE_REMOTE_ENDPOINTS 完整增强服务配置（最高优先级）
## - ONE_SIMPLE_JWT_AUTH_KEY 增强服务共用 JWT Key（简单配置 + 模板模式必须）
## - RSVC_BUNDLE_MYSQL_ENDPOINT_URL Mysql 增强服务地址
## - RSVC_BUNDLE_BKREPO_ENDPOINT_URL BKRepo 增强服务地址
## - RSVC_BUNDLE_RABBITMQ_ENDPOINT_URL RabbitMQ 增强服务地址
##
## 完整增强服务配置示例：
## SERVICE_REMOTE_ENDPOINTS:
##   - provision_params_tmpl:
##       engine_app_name: '{engine_app.name}'
##       operator: '{engine_app.name}'
##       egress_info: '{cluster_info.egress_info_json}'
##     jwt_auth_conf:
##       iss: paas-v3
##       key: example-jwt-key
##     prefer_async_delete: true
##     name: mysql_remote
##     endpoint_url: http://localhost:3306
##
## 若使用简化版本，则无需配置中的 SERVICE_REMOTE_ENDPOINTS 项，按以下步骤配置
## 1. 确认 ONE_SIMPLE_JWT_AUTH_KEY 项是否已配置妥当
## 2. Mysql: RSVC_BUNDLE_MYSQL_ENDPOINT_URL
##    BKRepo: RSVC_BUNDLE_BKREPO_ENDPOINT_URL
##    RabbitMQ: RSVC_BUNDLE_RABBITMQ_ENDPOINT_URL
## 按照以上映射表，配置您需要的增强服务，若 URL 值不会空，则加载配置时会按照预设模板渲染

# SERVICE_REMOTE_ENDPOINTS: []
## Mysql 增强服务地址
# RSVC_BUNDLE_MYSQL_ENDPOINT_URL: http://localhost:3306
## BKRepo 增强服务地址
# RSVC_BUNDLE_BKREPO_ENDPOINT_URL: http://localhost:8080
## RabbitMQ 增强服务地址
# RSVC_BUNDLE_RABBITMQ_ENDPOINT_URL: http://localhost:5672

## ------------------------------------ 应用市场相关配置 ------------------------------------

## 蓝鲸桌面数据库 Host
# BK_CONSOLE_DATABASE_HOST: ''
## 蓝鲸桌面数据库名称
# BK_CONSOLE_DATABASE_NAME: tencent_paas
## 蓝鲸桌面数据库相关配置
# BK_CONSOLE_DATABASE_OPTIONS: {}
## 蓝鲸桌面数据库访问密码
# BK_CONSOLE_DATABASE_PASSWORD: ''
## 蓝鲸桌面数据库端口
# BK_CONSOLE_DATABASE_PORT: 3306
## 蓝鲸桌面数据库访问 USER
# BK_CONSOLE_DATABASE_USER: root

## 是否强制要求填写应用联系人
# APP_REQUIRE_CONTACTS: false


## ------------------------------------ 平台日志相关配置 ------------------------------------

## 是否将 PaaS API 请求日志发送给 Redis 队列
# PAAS_API_LOG_REDIS_HANDLER:
#   enabled: false
#   url: redis://localhost:6379/0
#   queue_name: paas_ng-meters
#   tags: []


## ------------------------------------ 应用日志相关配置 ------------------------------------

## 日志 ES 服务地址
# ELASTICSEARCH_HOSTS:
#   - host: localhost
#     http_auth: username:pwd
#     port: 8080

## 日志 Index 名称模式
# ES_K8S_LOG_INDEX_PATTERNS: 'app_log-*'
## 接入层日志 Index 名称模式
# ES_K8S_LOG_INDEX_NGINX_PATTERNS: app_log-nginx-(?P<date>.+)


## ------------------------------------ 访问控制相关配置 ------------------------------------

## 访问控制主配置
# ACCESS_CONTROL_CONFIG: {}


## ------------------------------------ 访问统计相关配置 ------------------------------------

## 访问统计服务地址
# PAAS_ANALYSIS_BASE_URL: ''
## 访问统计 JWT 配置
# PAAS_ANALYSIS_JWT_CONF: {}


## ------------------------------------ 搜索服务相关配置 ------------------------------------

## 蓝鲸 PaaS3.0 资料库地址，用于搜索服务
# BKDOC_URL: http://localhost:8080

## 腾讯 iwiki 服务首页地址
# IWIKI_WEB_UI_BASE_URL: http://localhost:8080
## 腾讯 iwiki 服务 API 地址
# IWIKI_API_BASE_URL: http://localhost:8080
## iwiki 服务 Token
# IWIKI_API_RIO_GW_TOKEN: ''

## 腾讯码客服务 API 地址
# MK_SEARCH_API_BASE_URL: http://localhost:8080
## 腾讯码客服务 RIO Gateway Token
# MK_SEARCH_API_RIO_GW_TOKEN: ''
## 腾讯码客服务 Private Token
# MK_SEARCH_API_PRIVATE_TOKEN: ''


## ------------------------------------ 应用一键迁移配置 ------------------------------------

## 迁移时，是否 patch 用户代码
# IS_PATCH_CODE_IN_MGRLEGACY: true


## ------------------------------------ CI 相关配置 ------------------------------------

## 代码检查配置
# CODE_CHECK_CONFIGS: {}

# 开发者中心在蓝盾的项目 ID
BK_CI_PAAS_PROJECT_ID = bk_paas3"
# 云原生应用构建流水线 ID
BK_CI_BUILD_PIPELINE_ID = ""
# 云原生应用构建流水线调用用户（应使用虚拟账号）
BK_CI_CLIENT_USERNAME = "blueking"


## ------------------------------------ 蓝鲸文档中心配置 ------------------------------------

## 文档应用的应用ID
# BK_DOC_APP_ID: ''
## 蓝鲸官网文档中心地址
# BK_DOCS_URL_PREFIX: https://bk.tencent.com/docs
## PaaS 产品文档版本号，社区版年度大版本更新后需要更新对应的文档版本号
# BK_PAAS_DOCS_VER: 1.5

## 平台 FAQ 地址
# PLATFORM_FAQ_URL: http://localhost:8080
## 是否支持人工客服
# SUPPORT_LIVE_AGENT: false
## 人工客服配置
# LIVE_AGENT_CONFIG:
#   text: 联系客服
#   link: about:blank


## ------------------------------------ S-Mart 应用镜像化配置 ------------------------------------

## S-Mart 镜像仓库的 Registry 的域名
# SMART_DOCKER_REGISTRY_ADDR: registry.hub.docker.com

## S-Mart 镜像仓库的命名空间, 即在 Registry 中的项目名
# SMART_DOCKER_NAMESPACE: bkpaas/docker

## 用于访问 Registry 的账号
# SMART_DOCKER_USERNAME: bkpaas

## 用于访问 Registry 的密码
# SMART_DOCKER_PASSWORD: blueking

## 是否使用 DockerRegistryToken 来验证，为 false 时使用 HTTPBasicAuthentication
# SMART_DOCKER_AUTH_BY_TOKEN: true

## 如果用到 python manage.py push_smart_image, SMART_IMAGE_TAG 和 SMART_CNB_IMAGE_TAG 必须设置有效值
# SMART_IMAGE_TAG: v0.0.1-smart
# SMART_CNB_IMAGE_TAG: v0.0.1-smart

## ------------------------------------ 插件开发中心配置 ------------------------------------

## 插件中心「源码仓库」相关配置
# PLUGIN_REPO_CONF:
#  api_url: 'http://api.example.com/'
#  private_token: ''
#  email: 'blueking@tencent.com'
#  username: 'blueking'

## 插件开发中心在权限中心注册的系统 ID
# IAM_PLUGINS_CENTER_SYSTEM_ID: bk_plugins

## 是否在开发者中心应用列表中展示插件应用
# DISPLAY_BK_PLUGIN_APPS: true


## ------------------------------------ 蓝鲸监控配置 ------------------------------------

## 是否支持使用蓝鲸监控，启用后才能在社区版提供指标信息
# ENABLE_BK_MONITOR: false
## 蓝鲸监控运维相关的额外配置
# BKMONITOR_METRIC_RELABELINGS: {}
## 蓝鲸监控的API是否已经注册在 APIGW
# ENABLE_BK_MONITOR_APIGW: false
## 蓝鲸监控网关的环境
# BK_MONITOR_APIGW_SERVICE_STAGE: prod
## 监控增强服务的配置项, 其中 metric_name_prefix 是采集指标前缀, service_name 是注册到开发者中心的服务名
# RABBITMQ_MONITOR_CONF:
#    enabled: true
#    metric_name_prefix: ''
#    service_name: 'rabbitmq'
# BKREPO_MONITOR_CONF:
#    enabled: true
#    metric_name_prefix: ''
#    service_name: 'bkrepo'
# GCS_MYSQL_MONITOR_CONF:
#    enabled: true
#    metric_name_prefix: ''
#    service_name: 'gcs_mysql'

## ------------------------------------ 蓝鲸日志配置 ------------------------------------
# 默认的日志采集器类型, 可选值 "ELK", "BK_LOG"
# 低于 k8s 1.12 的集群不支持蓝鲸日志平台采集器, 如需要支持 k8s 1.12 版本(含) 以下集群, 默认值不能设置成 BK_LOG
# LOG_COLLECTOR_TYPE: "ELK"
# 蓝鲸日志平台的 API 是否已经注册在 APIGW，未注册则走 ESB 调用日志平台 API
# ENABLE_BK_LOG_APIGW: True
# 蓝鲸日志平台网关的环境，仅在 ENABLE_BK_LOG_APIGW=True 时生效
# BK_LOG_APIGW_SERVICE_STAGE: stag
# 蓝鲸日志平台相关的配置项
# BKLOG_CONFIG = {}

## ------------------------------------ 蓝鲸通知中心配置 ------------------------------------
# 通知中心的功能可通过配置开启
ENABLE_BK_NOTICE = False
# 对接通知中心的环境，默认为生产环境
BK_NOTICE_ENV = "prod"
# bk-notice-sdk 支持多租户需要显式配置 BK_APP_TENANT_ID=system
BK_APP_TENANT_ID = "system"

## ------------------------------------ 蓝鲸审计中心配置置 ------------------------------------
# 审计中心-审计配置-接入-数据上报中获取这两项配置信息的值
BK_AUDIT_DATA_TOKEN = ""
BK_AUDIT_ENDPOINT = ""

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

## slugbuilder build 的超时时间, 单位秒, 默认 15 分钟
# BUILD_PROCESS_TIMEOUT = 900


## ---------------------------------------- 服务导出配置 ----------------------------------------

## 默认容器内监听地址，默认 5000
# CONTAINER_PORT: 5000

## 服务相关插件配置
# SERVICES_PLUGINS: {}


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

## ------------------------------------ 原 workloads 配置，合并到 apiserver 中 ------------------------------------


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


## ---------------------------------------- 服务导出配置 ----------------------------------------

## 默认容器内监听地址，默认 5000
# CONTAINER_PORT: 5000

## 服务相关插件配置
# SERVICES_PLUGINS: {}


## ---------------------------------------- 沙箱相关配置 ----------------------------------------

# devserver 监听端口
DEV_SANDBOX_DEVSERVER_PORT: 8000
# devserver 镜像
DEV_SANDBOX_IMAGE: "bkpaas/dev-heroku-bionic:latest"

# 启动沙箱的数量上限
DEV_SANDBOX_COUNT_LIMIT: 5
# 沙箱跨域访问源地址
DEV_SANDBOX_CORS_ALLOW_ORIGINS: ""

# code editor 监听端口
DEV_SANDBOX_CODE_EDITOR_PORT: 8080
# code editor 镜像
DEV_SANDBOX_CODE_EDITOR_IMAGE: "codercom/code-server:4.9.0"

# 沙箱部署集群，若不配置则使用默认集群
DEV_SANDBOX_CLUSTER: ""

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


## ---------------------------------------- Ingress 配置 ----------------------------------------

## 当集群内存在多套 nginx controller 时, 需要设置 kubernetes.io/ingress.class 注解, 将 ingress 规则绑定到具体的 controller.
## - APP_INGRESS_CLASS 是子域名/子路径/独立域名三种 ingress 默认的 ingress.class 配置
## - CUSTOM_DOMAIN_INGRESS_CLASS 是独立域名特有的 ingress.class 配置, 优先级高于 APP_INGRESS_CLASS
##
## 配置项说明:
## 如果集群中只有一套 nginx controller, 通过 APP_INGRESS_CLASS 设置注解值即可, 不需要再单独设置 CUSTOM_DOMAIN_INGRESS_CLASS;
## 如果集群中有多套 nginx controller, 并且独立域名需要绑定具体 controller 时, 可以通过设置 CUSTOM_DOMAIN_INGRESS_CLASS 达到目的.
## 以蓝鲸私有化版本架构为例, 其采用了两层 nginx controller(第一层向第二层转发请求). 可以通过设置 CUSTOM_DOMAIN_INGRESS_CLASS 将独立域名
## 绑定到第一层的 controller, 而子路径通过设置 APP_INGRESS_CLASS 绑定到第二层的 controller.
# APP_INGRESS_CLASS = ''
# CUSTOM_DOMAIN_INGRESS_CLASS = ''


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

## ---------------------------------------- Egress 配置 ----------------------------------------

## BCS Egress Gate 镜像地址
# BCS_EGRESS_GATE_IMAGE: 'hub.bktencent.com/bcs/gate:1.0.0'

## BCS Egress PodIP 镜像地址
# BCS_EGRESS_POD_IP_IMAGE: 'hub.bktencent.com/bcs/podip:1.0.0'

## 应用服务 Pod IP 可分配网段
# BCS_EGRESS_POD_CIDRS:
#  - 127.0.0.1/16
#  - 192.168.0.0/16

## ---------------------------------------- 监控数据配置 ----------------------------------------

## 指标服务相关 Token 配置
# METRIC_CLIENT_TOKEN_DICT:
#   bkmonitor: example-metric-client-token

## 调用 Healthz API 需要的 Token
# HEALTHZ_TOKEN: example-healthz-token

## 插件监控图表相关配置
# MONITOR_CONFIG:
#   metrics:
#     bkmonitor:
#       basic_auth:
#         - bkmonitor-api
#         - example-auth-token
#       host: http://bkmonitor-query.example.com

## ------------------------------------ 安全配置 ------------------------------------

# FORBIDDEN_REPO_PORTS 包含与代码/镜像仓库相关的敏感端口，配置后，平台将不允许用户填写或注册相关的代码/镜像仓库
FORBIDDEN_REPO_PORTS = [21, 22, 23]

## ------------------------------------ internal 配置，仅开发项目与特殊环境下使用 ------------------------------------

## 运维开发相关的 BK-DATA 数据上报相关配置
# PAAS_X_BK_DATA_DB_CONF: {}

## （调试用）强制不检查 CSRF，注意：与 Django DEBUG 无直接关系
# DEBUG_FORCE_DISABLE_CSRF: false

## Sentry 服务配置，包含 DSN 等，配置示例：{"dsn": "http://example-sentry-dsn"}
# SENTRY_CONFIG: {}

## 是否开启 OTEL 数据上报，默认值为 false
# ENABLE_OTEL_TRACE: false
## 是否记录 DB 相关 tracing
# OTEL_INSTRUMENT_DB_API: True
## 上报数据服务名称，一般不需要修改
# OTEL_SERVICE_NAME: bkpaas3-apiserver
## sdk 采样规则（always_on / always_off / parentbased_always_on...）
# OTEL_SAMPLER: always_on
## OTEL 上报到监控平台的数据 Token，可通过监控平台上新建应用获得
# OTEL_BK_DATA_TOKEN: -1
## OTEL 上报地址（grpc）
# OTEL_GRPC_URL: http://localhost:8080

## 本选项默认关闭。表示注入到应用运行环境中的 {prefix}_SUB_PATH 环境变量总是使用真实值（基于算法的最短子路径）。
## 开启后将总是使用静态值：{region}-{engine-app-name} ，仅限特殊路由规则的部署环境启用。
# FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE: false

## 初始化的第三方应用(外链应用)的 code,多个以英文逗号分割
# THIRD_APP_INIT_CODES: ''

## 允许通过 API 创建第三方应用(外链应用)的系统ID,多个以英文逗号分割
# ALLOW_THIRD_APP_SYS_IDS: ""

## 测试用 k8s apiserver 地址
# FOR_TESTS_APISERVER_URL： 'http://localhost:28080'

## 测试用 k8s 证书相关数据
# FOR_TESTS_CA_DATA: ''
# FOR_TESTS_CERT_DATA: ''
# FOR_TESTS_KEY_DATA: ''

## 测试用 k8s 集群 Bearer Token
# FOR_TESTS_TOKEN_VALUE: ''

## 在请求 APIServer 时, 使用该 hostname 替换具体的 backend 中的 hostname
# FOR_TESTS_FORCE_DOMAIN: ''

## 测试 ingress end-to-end 用特殊配置
# FOR_TEST_E2E_INGRESS_CONFIG: {}
