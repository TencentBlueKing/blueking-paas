## app-spark-api 配置模板
##
## 这是所有配置项的权威参考：每一项都标了「必填」「可选」或「按条件必填」，可选项写的是默认值。
## 本地开发可以把它复制为 manage.py 同目录下的 settings_local.yaml，取消注释并填写需要的项。
## 每一项也可以用加了 APP_SPARK_API_ 前缀的环境变量设置，环境变量优先，详见 app_spark_api/settings/__init__.py。

## ---------------------------------- Django 基础 ----------------------------------

## 可选。默认值不安全，部署时必须换成随机生成的值：
## python -c "import secrets; print(secrets.token_urlsafe(50))"
# SECRET_KEY: ''
## 可选，默认 false。
# DEBUG: false
## 可选，默认 ['*']。
# ALLOWED_HOSTS: ['*']

## 可选。子路径部署时的对外前缀，Ingress 会先剥掉它再转给本服务；空字符串等同于部署在站点根路径。
# FORCE_SCRIPT_NAME: ''
## 可选。未配置时：有 FORCE_SCRIPT_NAME 则为 {FORCE_SCRIPT_NAME}/static/，否则为 /static/。
# STATIC_URL: /static/

## 可选，默认 67108864（64MB）。请求体读入内存的上限（字节）。不要调回 Django 默认的 2.5MB：
## Runtime 回写状态走普通 JSON 请求体，一份会话上下文序列化后远超这个大小。
# DATA_UPLOAD_MAX_MEMORY_SIZE: 67108864

## ---------------------------------- 日志 ----------------------------------

## 可选，默认 INFO。
# LOG_LEVEL: INFO
## 可选。配置后改为写入这个目录下的滚动日志文件（相对路径基于 manage.py 所在目录），不再写控制台。
# LOGGING_DIRECTORY: ''
## 可选，默认 false。配置了 LOGGING_DIRECTORY 时是否仍同时写控制台。
# LOGGING_ALWAYS_CONSOLE: false

## ---------------------------------- 应用身份与用户 ----------------------------------

## 必填。本服务在蓝鲸的应用身份，调用蓝鲸各服务（登录验票、调开发者中心）都用这一对。
## APP_SECRET 只留在本服务里，不会交给 Agent Runtime。
# APP_CODE: ''
# APP_SECRET: ''

## 按条件必填：AGENT_MODEL_SOURCE 为 bkaidev 时必填。签发 Agent 用户态 access_token 的专用应用（如 app-spark-pub），
## 不回落到 APP_CODE。换来的 token 会进入用户沙箱，这个应用只应申请 bkaidev 大模型调用的权限。
# USER_ACCESS_TOKEN_APP_CODE: ''
# USER_ACCESS_TOKEN_APP_SECRET: ''

## 可选，默认 false。是否启用多租户模式，只能在初次部署时配置，部署后不支持调整。
# ENABLE_MULTI_TENANT_MODE: false

## 可选，默认 true。是否自动为访问用户创建 profile，即站点是否对全员开放。
# AUTO_CREATE_REGULAR_USER: true

## ---------------------------------- 国际化 ----------------------------------

## 均可选。语言 cookie 必须和整个蓝鲸体系保持一致。
# LANGUAGE_CODE: zh-hans
# LANGUAGES:
#   - [zh-hans, 简体中文]
#   - [en, English]
# TIME_ZONE: Asia/Shanghai
# LANGUAGE_COOKIE_NAME: blueking_language
# LANGUAGE_COOKIE_PATH: /
## 可选，默认取 BK_COOKIE_DOMAIN。
# LANGUAGE_COOKIE_DOMAIN: ''
## 可选。蓝鲸 cookie 所在的域，LANGUAGE_COOKIE_DOMAIN 未配置时使用。
# BK_COOKIE_DOMAIN: ''

## ---------------------------------- 数据库与队列 ----------------------------------

## 必填。MySQL 8.0 以上，引擎固定为 MySQL。未配置 DATABASE_NAME 时只有不需要数据库的管理命令能执行。
# DATABASE_NAME: app_spark
# DATABASE_USER: ''
# DATABASE_PASSWORD: ''
# DATABASE_HOST: ''
# DATABASE_PORT: ''
## 可选，默认 {}。
# DATABASE_OPTIONS: {}

## 按条件必填：项目自动命名、发布到开发者中心都要投递 Celery 任务，用到它们时必填。
## 没写时用占位默认值，进程能起来、启动时不探测队列，但任务投递不出去。口令不要写进仓库。
# RABBITMQ_HOST: ''
# RABBITMQ_PORT: 5672
# RABBITMQ_USER: ''
# RABBITMQ_PASSWORD: ''
# RABBITMQ_VHOST: ''

## 可选。默认用本地临时文件缓存，只适用于本地开发。多副本或多 worker 部署时必须配远程缓存（如 RedisCache、
## DatabaseCache），否则各进程的缓存不一致。
# DEFAULT_CACHE_CONFIG:

## 可选。列表接口固定用「页码 + 每页条数」翻页。默认每页条数，客户端可用 page_size 覆盖。
# NINJA_PAGINATION_PER_PAGE: 20
## 可选。每页条数上限，客户端传更大的值会被压回这个数。
# NINJA_MAX_PER_PAGE_SIZE: 100

## 必填，没有默认值，缺了进程起不来。数据库字段（如仓库 token）加密用的 Fernet key，必须保持稳定，
## 换了就解不开已有数据：
## python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# BKKRILL_ENCRYPT_SECRET_KEY: ''
## 可选，默认 FernetCipher。
# ENCRYPT_CIPHER_TYPE: FernetCipher

## ---------------------------------- 蓝鲸登录（bkpaas_auth） ----------------------------------

## 必填。统一登录页面地址，未登录时前端跳转到这里。
# LOGIN_FULL: ''

## 可选，默认 bk_token。用户身份校验类型，也是登录 cookie 的名字（bk_token 或 bk_ticket）；
## 同时决定换 access_token 的 backend：bk_token 用 SSM，其余用 auth api。
# BKAUTH_BACKEND_TYPE: bk_token
## 可选，默认 prod。bk-login 网关的环境名。
# BKAUTH_BK_LOGIN_APIGW_STAGE: prod
## 按条件必填，以下两项至少配一项：
## - BKAUTH_USER_INFO_APIGW_URL：经 bk-login 网关校验用户身份，配了它就忽略 BKAUTH_USER_COOKIE_VERIFY_URL。
##   ENABLE_MULTI_TENANT_MODE 为 true 时必须配它；
## - BKAUTH_USER_COOKIE_VERIFY_URL：环境里没有 bk-login 网关时，用这个地址校验登录态。
# BKAUTH_USER_INFO_APIGW_URL: ''
# BKAUTH_USER_COOKIE_VERIFY_URL: ''
## 可选。通过 token 获取用户信息的 API。
# BKAUTH_TOKEN_USER_INFO_ENDPOINT: ''

## ---------------------------------- 蓝鲸 API 网关 ----------------------------------

## 按条件必填：走 bkaidev 网关调模型、发布到开发者中心时必填。网关 API 地址模板，须含 {api_name}，例如：
##   https://bkapi.example.com/api/{api_name}/
##   https://{api_name}.apigw.example.com
# BK_API_URL_TMPL: ''

## 可选，默认 prod。调用网关时的环境名（stage），各网关没有单独配置时都用它。
# APIGW_ENVIRONMENT: prod
## 可选，默认取 APIGW_ENVIRONMENT。bkaidev 网关单独用的环境名。
# BKAIDEV_APIGW_ENVIRONMENT: prod
## 可选，默认取 APIGW_ENVIRONMENT。开发者中心网关单独用的环境名。
# BKPAAS_APIGW_ENVIRONMENT: stag

## 按条件必填：AGENT_MODEL_SOURCE 或 LLM_SOURCE 为 bkaidev 时必填。用户态 access_token 的签发地址，
## 不从 BK_API_URL_TMPL 拼，按部署版本填。backend 由 BKAUTH_BACKEND_TYPE 决定。
# TOKEN_AUTH_ENDPOINT: ''
## 可选，默认 prod。换票请求体里的 env_name（prod / test），BKAUTH_BACKEND_TYPE 为 bk_token 时不使用。
# AUTH_ENV_NAME: prod

## ---------------------------------- 源码仓库与制品库 ----------------------------------

## 必填。Git 持久化没有关闭开关：创建 Project 时就要建仓，仓库没就绪不会拉起 Agent。
## 不配时有一份指向 repo-server.invalid 的默认值，只为让进程能起来，真正建仓时会失败。
# REPO_SERVER:
#   ## 可选，默认 forgejo，目前只实现了 forgejo。
#   type: forgejo
#   ## 必填。本服务调 Forgejo API 的地址。
#   base_url: ''
#   ## 必填。Agent 和 git 看到的地址。只在所有东西都跑在同一台机器上时才和 base_url 相同，
#   ## 沙箱里的 Agent 访问不到本服务看到的 localhost，所以不要默认写成 localhost。
#   clone_url: ''
#   ## 必填。所有 Project 仓库都建在这个组织下。
#   org: app-spark
#   ## 必填。用它的密码签发和吊销仓库 token，不能开两步验证。
#   service_account: app-spark-bot
#   service_account_password: ''
#   ## 以下均可选。工作分支、Forgejo API 超时秒数、Agent 提交时的身份。
#   default_branch: main
#   timeout_seconds: 30.0
#   commit_author_name: App-Spark
#   commit_author_email: app-spark@localhost.invalid

## 按条件必填：发布到开发者中心、或 AGENT_CONTEXT_STORAGE.backend 为 bk_repo 时必填。
## 发布用的源码包要签预签名下载地址，只能存在制品库。四个字段都必填。
# BLOBSTORE_BKREPO_CONFIG:
#   PROJECT: ''
#   ENDPOINT: ''
#   USERNAME: ''
#   PASSWORD: ''
## 可选，默认 app-spark-source-packages。存放源码包的通用仓库名，需事先在上面的 PROJECT 下建好。
# BLOBSTORE_BUCKET_SOURCE_PACKAGES: app-spark-source-packages

## ---------------------------------- Agent Runtime provider ----------------------------------

## 可选，默认 local_process。怎么为会话拉起 Agent Runtime：
## - local_process：在本机 spawn agent 进程，预览由本服务转发，仅供开发和测试；
## - e2b：每个会话一个沙箱，预览由浏览器直接打开沙箱的地址，用于生产和预发布。
# AGENT_RUNTIME_PROVIDER: local_process

## 必填。上面所选 provider 的配置，两种 provider 的字段不同，只写所选那一种。
##
## local_process：
# AGENT_RUNTIME_PROVIDER_CONFIG:
#   ## 必填。agent 项目目录，uv run --project 指向它。
#   agent_project_dir: ../agent
#   ## 必填。各 Project 的 workspace 的父目录，实际工作目录为 {workspace_root}/{project_id}。
#   workspace_root: /tmp/app-spark/workspaces
#   ## 必填。各会话状态目录的父目录，不能在 workspace_root 里，否则 Agent 自己的文件工具能改掉自己的历史。
#   state_root: /tmp/app-spark/agent-state
#   ## 可选，默认 http://127.0.0.1:8000。agent 进程访问本服务、回写会话状态用的地址。
#   callback_base_url: http://127.0.0.1:8000
#   ## 可选，默认 60。等新起的 Runtime 通过 /health 的超时秒数。
#   startup_timeout_seconds: 60
#   ## 可选。其余要透给 agent 进程的 APP_SPARK_AGENT_* 变量；模型相关的变量不收，由 AGENT_MODEL_SOURCE 决定。
#   extra_env: {}
##
## e2b：
# AGENT_RUNTIME_PROVIDER_CONFIG:
#   ## 必填。自建 E2B 兼容服务的 API 凭据和管理 API 地址，不使用 SDK 的公共默认值。
#   api_key: ''
#   api_url: https://example.com/e2b
#   ## 必填。本服务的对外地址，沙箱内的 Agent 经 Ingress 用它回写会话状态。
#   callback_base_url: https://app-spark.example.com
#   ## 必填。预装了 Agent 的沙箱模板，由 agent 镜像添加而来，没有默认值。
#   template: app-spark-agent
#   ## 可选。API 未返回 sandbox_domain 时使用的域名后缀。
#   domain: example.com
#   ## 可选，默认 1800。沙箱空闲多少秒后回收，同时作为 Agent 的空闲退出时间；每轮开始和结束时续期，
#   ## 预览和查询状态不续期。
#   idle_timeout_seconds: 1800
#   ## 可选，默认 86400。沙箱最长存活秒数，超过后在下一轮开始前重建，不打断进行中的一轮。必须比 E2B 平台
#   ## 自己的沙箱存活上限小，至少留出最长一轮的时间，否则平台到点直接销毁沙箱，Agent 来不及推送。
#   max_lifetime_seconds: 86400
#   ## 可选，默认 8000 / 9000，所有沙箱相同。Agent 监听的端口和用户应用监听的预览端口。
#   runtime_port: 8000
#   preview_port: 9000
#   ## 可选，默认 https。暴露端口的协议。平台页面是 https 时这里也必须是 https，否则预览会被浏览器拦掉。
#   port_scheme: https
#   ## 可选。沙箱内 Agent 的 workspace 与状态目录，必须是绝对路径且不能互相包含。
#   workspace_dir: /data/workspace
#   state_dir: /data/state
#   ## 可选。在沙箱内启动 Agent 的单条命令。envd 不继承镜像的 PATH，所以默认用绝对路径。
#   agent_command: /app/.venv/bin/python -m app_spark_agent
#   ## 可选，默认 user。在沙箱内启动、停止、探测 Agent 和读日志所用的用户，必须存在于模板里。
#   agent_user: user
#   ## 可选。Agent 日志在沙箱内的路径，启动失败时截取末尾返回。
#   agent_log_path: /tmp/app-spark-agent.log
#   ## 可选，默认 60。等 Agent 通过 /health 的超时秒数。
#   startup_timeout_seconds: 60
#   ## 可选。其余要透给 Agent 的 APP_SPARK_AGENT_* 变量，规则与 local_process 相同。
#   extra_env: {}

## ---------------------------------- Agent 的模型 ----------------------------------

## 可选，默认 bkaidev。Agent Runtime 调模型走哪条路：
## - bkaidev：走 bkaidev 网关，拉起 Runtime 时用当前用户的登录态换一张用户态 access_token 交给它。
##   需要 BK_API_URL_TMPL、TOKEN_AUTH_ENDPOINT、USER_ACCESS_TOKEN_APP_CODE / USER_ACCESS_TOKEN_APP_SECRET；
## - direct：直连模型厂商，用 AGENT_DIRECT_MODEL_CONFIG 里固定的 key。
# AGENT_MODEL_SOURCE: bkaidev

## 按条件必填：AGENT_MODEL_SOURCE 为 direct 时必填。
# AGENT_DIRECT_MODEL_CONFIG:
#   ## 必填。pydantic-ai 的 <provider>:<model>；本地不花钱跑通用 fake:write-file。
#   model: deepseek:deepseek-v4-flash
#   ## 按条件必填，fake: 模型不需要。厂商 API Key。
#   api_key: ''
#   ## 以下均可选，只用于模型列表展示，不注入 Runtime。name 默认取 model 冒号后的部分，
#   ## context_window 是上下文窗口的 token 数，默认未知。
#   name: DeepSeek V4 Flash
#   context_window: 128000

## 可选，AGENT_MODEL_SOURCE 为 bkaidev 时使用。LLM 基址不在这里配，由
## {BK_API_URL_TMPL:bkaidev}/{BKAIDEV_APIGW_ENVIRONMENT}/openapi/aidev/gateway/llm/v1 拼出。
# BKAIDEV_MODEL_CONFIG:
#   ## 可选，默认 deepseek-v4-flash。第一顺位的默认模型，不在可选列表里时取列表第一个。
#   default_model_id: deepseek-v4-flash
#   ## 可选，默认为空即不过滤。可选模型的 ID 或通配模式（fnmatch，区分大小写），顺序即展示顺序。
#   available_models:
#     - deepseek-*-flash
#     - hy4-*
#     - qwen3-5-397B

## ---------------------------------- 本服务调用的模型 ----------------------------------

## 可选，默认 bkaidev。本服务自己调模型（给项目起名）走哪条路，与 AGENT_MODEL_SOURCE 分开配：
## - bkaidev：走 bkaidev 网关，基址与 Agent 相同，凭建项目时换好的用户态 access_token 调用；
## - direct：直连模型厂商，用 LLM_DIRECT_CONFIG 里固定的 key；
## - fake：不发起网络请求的假模型，本地不花钱跑通链路用。
# LLM_SOURCE: bkaidev
## 可选，默认 deepseek-v4-flash。LLM_SOURCE 为 bkaidev 时使用的模型 ID，不带厂商前缀。
# LLM_BKAIDEV_MODEL_ID: deepseek-v4-flash
## 按条件必填：LLM_SOURCE 为 direct 时必填，两个字段都必填。
# LLM_DIRECT_CONFIG:
#   ## pydantic-ai 的 <provider>:<model>。
#   model: deepseek:deepseek-v4-flash
#   api_key: ''
## 可选，默认 30。单次模型请求的超时秒数。
# LLM_TIMEOUT_SECONDS: 30

## ---------------------------------- 会话状态 ----------------------------------

## 可选，默认如下。会话上下文存在哪，一份上下文可能有好几 MB，所以存 blob 而不是数据库行。backend 可选：
## - host_tmp_path：root 为本机父目录，只适合单副本；
## - bk_repo：root 为制品库通用仓库名，多副本 e2b 必须用它，需要 BLOBSTORE_BKREPO_CONFIG。
# AGENT_CONTEXT_STORAGE:
#   backend: host_tmp_path
#   root: /tmp/app-spark/agent-contexts

## 可选，默认 5。一个会话保留的最近上下文版本数。小于 1 按 1 算，冷启动只读最新一版。
# AGENT_CONTEXT_VERSIONS_KEPT: 5
## 可选，默认 3。一个会话保留的最近检查点数。冷启动只用最新一个，其余供排查。
# AGENT_CHECKPOINTS_KEPT: 3

## ---------------------------------- 发布到开发者中心 ----------------------------------

## 可选，默认 bkpaas3。开发者中心在 API 网关上的网关名，发布和建项目时注册用户都用它与 BK_API_URL_TMPL 拼地址。不同版本的开发者中心不一样。
# BKPAAS_APIGW_NAME: bkpaas3
## 可选。开发者中心前端站点地址，只用来拼发布结果里的页面链接；留空时不返回这些链接，发布本身不受影响。
# BKPAAS_URL: ''
