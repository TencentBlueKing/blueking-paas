## app-spark-api 配置模板

## Django 基础配置
# SECRET_KEY: ''
# DEBUG: false
# ALLOWED_HOSTS: ['*']

## 国际化
# LANGUAGE_CODE: zh-hans
# LANGUAGES:
#   - [zh-hans, 简体中文]
#   - [en, English]
# TIME_ZONE: Asia/Shanghai
# LANGUAGE_COOKIE_NAME: blueking_language
# LANGUAGE_COOKIE_PATH: /
# LANGUAGE_COOKIE_DOMAIN: ''

## 数据库（引擎固定为 MySQL，必填）
## 未配置 DATABASE_NAME 时服务无法正常启动（仅部分无需数据库的管理命令可执行）
# DATABASE_NAME: app_spark
# DATABASE_USER: ''
# DATABASE_PASSWORD: ''
# DATABASE_HOST: ''
# DATABASE_PORT: ''
# DATABASE_OPTIONS: {}

## 缓存
## 优先级最高，若不配置则默认使用本地临时文件缓存（仅适用于本地开发）
## 生产环境请配置远程服务缓存（如 RedisCache、DatabaseCache），以保证多副本多 worker 时缓存数据一致
# DEFAULT_CACHE_CONFIG:

## 列表接口翻页（翻页方式固定为「页码 + 每页条数」，不可配置）
## 默认每页条数，客户端可用 page_size 参数覆盖，但不能超过下面的上限
# NINJA_PAGINATION_PER_PAGE: 20
## 每页条数上限，客户端传更大的值会被压回这个数
# NINJA_MAX_PER_PAGE_SIZE: 100

## Project 源码使用蓝鲸制品库时的连接配置，仅基础配置，具体仓库名和 key 在各 Project 对应模型中
# BLOBSTORE_BKREPO_CONFIG:
#   PROJECT: ''
#   ENDPOINT: ''
#   USERNAME: ''
#   PASSWORD: ''

## ---------------------------------- Agent Runtime 驱动相关配置 ----------------------------------

## 用什么方式为一个会话拉起 Agent Runtime，目前只有 local_process
## （在本机 spawn 一个 agent 进程，仅供开发与测试；需先在 agent 目录执行过 uv sync）
# AGENT_RUNTIME_PROVIDER: local_process

## 上述驱动方式各自的配置，字段以对应的 config 类为准（local_process 见 LocalProcessConfig）
# AGENT_RUNTIME_PROVIDER_CONFIG:
#   ## agent 项目目录，即 agent 的 pyproject.toml 所在处
#   agent_project_dir: ''
#   ## 各 Project 的 workspace 的父目录
#   workspace_root: ''
#   ## 各会话的状态目录的父目录，必须在 workspace_root 之外，否则 agent 可能用自己的文件工具毁掉自己的历史
#   state_root: ''
#   ## 传给 agent 的 APP_SPARK_AGENT_MODEL / APP_SPARK_AGENT_MODEL_API_KEY，不填则用 agent 自己的默认值
#   model: ''
#   model_api_key: ''
#   ## 等待新起的 Runtime 变健康的超时秒数
#   startup_timeout_seconds: 60
#   ## 其余要透给 agent 进程的 APP_SPARK_AGENT_* 变量
#   extra_env: {}

## 是否启用多租户模式，仅支持在初次部署时配置，部署后不支持动态调整
# ENABLE_MULTI_TENANT_MODE: false

## 是否自动为当前访问用户创建用户 profile，即站点是否对全员默认开放
# AUTO_CREATE_REGULAR_USER: true

## ---------------------------------- 各系统地址相关配置 ----------------------------------

## 统一登录页面地址，用于模板渲染，必填
# LOGIN_FULL: ''

## -------------------------------- 用户鉴权模块 bkpaas_auth SDK 相关配置 --------------------------------

## 用户身份校验类型，默认值为 bk_token
# BKAUTH_BACKEND_TYPE: bk_token
## 用于获取 Token 的 App Code
# BKAUTH_TOKEN_APP_CODE: ''
## 用于获取 Token 的 App Secret
# BKAUTH_TOKEN_SECRET_KEY: ''
## bk-login 网关环境，默认值为 prod
# BKAUTH_BK_LOGIN_APIGW_STAGE: prod
## 如果当前环境没有 bk-login 网关，则设置 BKAUTH_USER_INFO_APIGW_URL 为空字符串，bkpaas_auth 将使用 BKAUTH_USER_COOKIE_VERIFY_URL
## 如果设置了有效的 BKAUTH_USER_INFO_APIGW_URL，BKAUTH_USER_COOKIE_VERIFY_URL 配置将被忽略，使用网关进行用户身份校验
## 多租户模式下（BKAUTH_ENABLE_MULTI_TENANT_MODE=true）必须设置有效的 BKAUTH_USER_INFO_APIGW_URL
# BKAUTH_USER_INFO_APIGW_URL: ''
## 验证用户登录态（是否过期）的地址
# BKAUTH_USER_COOKIE_VERIFY_URL: ''
## 通过 Token 获取用户信息 API
# BKAUTH_TOKEN_USER_INFO_ENDPOINT: ''

## 更多参考：https://docs.djangoproject.com/zh-hans/6.1/ref/settings/#force-script-name
# FORCE_SCRIPT_NAME: ''

## 静态资源。未配置时：有 FORCE_SCRIPT_NAME 则为 {FORCE_SCRIPT_NAME}/static/，否则为 /static/
# STATIC_URL: /static/
