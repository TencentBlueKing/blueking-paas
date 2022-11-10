# type: ignore
"""PaaS Workload service settings

默认情况下，本项目会读取根目录（manage.py 所在目录）下的 `settings_files` 子目录内的所有
YAML 文件和 `settings_local.yaml` 的内容，将其作为配置项使用。你也可以用 `PAAS_WL_SETTINGS`
环境变量指定其他配置文件，比如：

    # 多个配置文件使用 ; 分割
    export PAAS_WL_SETTINGS='common.yaml;dev.yaml'

指定其他文件后，`settings_files/*.yaml` 与 `settings_local.yaml` 仍然会生效，最终
配置会是所有内容合并后的结果。

除了 YAML 外，每个配置项也可通过环境变量设置。比如，在 YAML 文件里的配置项 `SECRET_KEY: foo`，
也可使用以下环境变量修改：

    export PAAS_WL_SECRET_KEY="foo"

注意事项：

- 必须添加 `PAAS_WL_` 前缀
- 环境变量比 YAML 配置的优先级更高
- 环境变量可修改字典内的嵌套值，参考文档：https://www.dynaconf.com/envvars/
"""
import copy
from pathlib import Path

from bkpaas_auth.core.constants import ProviderType
from django.utils.encoding import force_bytes, force_str
from dynaconf import LazySettings, Validator

from .utils import (
    get_database_conf,
    get_default_keepalive_options,
    get_internal_services_jwt_auth_conf,
    get_paas_service_jwt_clients,
    is_redis_backend,
    is_redis_sentinel_backend,
)

BASE_DIR = Path(__file__).parents[2]

SETTINGS_FILES_GLOB = str(BASE_DIR / 'settings_files/*.yaml')
LOCAL_SETTINGS = str(BASE_DIR / 'settings_local.yaml')

settings = LazySettings(
    environments=False,
    load_dotenv=True,
    # Read settings files in below locations
    includes=[SETTINGS_FILES_GLOB, LOCAL_SETTINGS],
    validators=[
        # Configure minimal required settings
        Validator('BKKRILL_ENCRYPT_SECRET_KEY', must_exist=True),
    ],
    # Envvar name configs
    ENVVAR_PREFIX_FOR_DYNACONF="PAAS_WL",
    ENVVAR_FOR_DYNACONF="PAAS_WL_SETTINGS",
)

# ---------------
# 全局配置
# ---------------

# 用于加密数据库内容的 secret
BKKRILL_ENCRYPT_SECRET_KEY = force_bytes(settings.get('BKKRILL_ENCRYPT_SECRET_KEY', ''))

# 如果 SECRET_KEY 没有配置，使用 BKKRILL 的 secret key 替代
SECRET_KEY = settings.get("SECRET_KEY") or force_str(BKKRILL_ENCRYPT_SECRET_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = settings.get('DEBUG', False)

ALLOWED_HOSTS = settings.get('ALLOWED_HOSTS', ['*'])

MIDDLEWARE = (
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'paas_wl.tracing.middlewares.RequestIDProvider',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'blue_krill.auth.client.VerifiedClientMiddleware',
    'paas_wl.platform.applications.middlewares.InstancesInPlaceMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
)

ROOT_URLCONF = 'paas_wl.urls'

WSGI_APPLICATION = 'paas_wl.wsgi.application'

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'paas_wl.utils.views.custom_exception_handler',
    'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.serializers.ModelSerializer',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_AUTHENTICATION_CLASSES': ('paas_wl.platform.auth.authentication.AsInternalUserAuthentication',),
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    # TIPS: 覆盖 SearchFilter、OrderingFilter 的过滤参数，与应用列表保持用同样的搜索、排序字段
    'SEARCH_PARAM': 'search_term',
    'ORDERING_PARAM': 'order_by',
}

# ---------------
# Django App 配置
# ---------------
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'bkpaas_auth',
    'drf_yasg',
    'django_prometheus',
    'paas_wl.platform.misc',
    'paas_wl.platform.applications',
    'paas_wl.cluster',
    'paas_wl.monitoring.metrics',
    'paas_wl.networking.egress',
    'paas_wl.networking.ingress',
    'paas_wl.workloads.resource_templates',
    'paas_wl.release_controller.hooks',
    'paas_wl.workloads.processes',
    'paas_wl.workloads.images',
    'paas_wl.monitoring.app_monitor',
    'paas_wl.cnative.specs',
]

# ---------------
# 国际化
# ---------------
LANGUAGE_CODE = 'zh-cn'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# ---------------
# 静态文件配置
# ---------------
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/
STATIC_URL = '/static/'


DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# ---------------
# 模版文件配置
# ---------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        },
    }
]

# ---------------
# 数据库，日志与存储配置
# ---------------

DATABASES = {"default": get_database_conf(settings)}

LOG_LEVEL = settings.get('LOG_LEVEL', default='INFO')

# 配置该 handler 后，所有日志等将被送往该 Redis 管道
LOGGING_REDIS_HANDLER = settings.get('LOGGING_REDIS_HANDLER')

if not LOGGING_REDIS_HANDLER:
    _redis_handler = {'level': 'DEBUG', 'class': 'logging.NullHandler'}
else:
    _redis_handler = LOGGING_REDIS_HANDLER

_default_handlers = ['console', 'logstash_redis']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s [%(asctime)s] [%(request_id)s] %(name)s(ln:%(lineno)d): %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {'format': '%(levelname)s %(message)s'},
    },
    'filters': {'request_id': {'()': 'paas_wl.utils.log.RequestIDFilter'}},
    'handlers': {
        'null': {'level': LOG_LEVEL, 'class': 'logging.NullHandler'},
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
        'logstash_redis': _redis_handler,
    },
    'loggers': {
        'django': {'handlers': ['null'], 'level': LOG_LEVEL, 'propagate': True},
        'root': {'handlers': _default_handlers, 'level': LOG_LEVEL, 'propagate': False},
        'paas_wl': {'handlers': _default_handlers, 'level': LOG_LEVEL},
        'api': {'handlers': _default_handlers, 'level': LOG_LEVEL},
        'scheduler': {'handlers': _default_handlers, 'level': LOG_LEVEL},
        'requests': {'handlers': _default_handlers, 'level': LOG_LEVEL},
        # Special loggers
        'commands': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'django.request': {'handlers': _default_handlers, 'level': 'ERROR', 'propagate': False},
    },
}

if settings.get('LOGGING_ENABLE_SQL_QUERIES', False):
    LOGGING['loggers']['django.db.backends'] = {'handlers': _default_handlers, 'level': LOG_LEVEL, 'propagate': True}


# ---------------
# 运行时默认配置
# ---------------
DEFAULT_SLUGRUNNER_IMAGE = settings.get('DEFAULT_SLUGRUNNER_IMAGE', 'bkpaas/slugrunner')
DEFAULT_SLUGBUILDER_IMAGE = settings.get('DEFAULT_SLUGBUILDER_IMAGE', 'bkpaas/slugbuilder')

BUILDER_USERNAME = settings.get('BUILDER_USERNAME', 'blueking')

# 构建 Python 应用时，强制使用该地址覆盖 PYPI Server 地址
PYTHON_BUILDPACK_PIP_INDEX_URL = settings.get('PYTHON_BUILDPACK_PIP_INDEX_URL')

# 从源码构建应用时，注入额外环境变量
BUILD_EXTRA_ENV_VARS = settings.get('BUILD_EXTRA_ENV_VARS', {})

# ---------------
# 对象存储配置
# ---------------
BLOBSTORE_TYPE = settings.get('BLOBSTORE_TYPE')

BLOBSTORE_S3_ENDPOINT = settings.get('BLOBSTORE_S3_ENDPOINT', default='http://127.0.0.1:9100')
BLOBSTORE_S3_ACCESS_KEY = settings.get('BLOBSTORE_S3_ACCESS_KEY', default='minio')
BLOBSTORE_S3_SECRET_KEY = settings.get('BLOBSTORE_S3_SECRET_KEY', default='')
# 应用构建 SLUG 存放 bucket 名，默认无需修改，应和 apiserver 中 BLOBSTORE_BUCKET_APP_SOURCE 保持一致
BLOBSTORE_S3_BUCKET_NAME = settings.get('BLOBSTORE_S3_BUCKET_NAME', default='bkpaas3-slug-packages')

# These configs are must for minio server
BLOBSTORE_S3_REGION_NAME = settings.get('BLOBSTORE_S3_REGION_NAME', 'us-east-1')
BLOBSTORE_S3_SIG_VERSION = settings.get('BLOBSTORE_S3_SIG_VERSION', 's3v4')

# 当配置该项时，使用 BK-Repo 而不是 S3 作为 BlobStore 存储
BLOBSTORE_BKREPO_CONFIG = settings.get('BLOBSTORE_BKREPO_CONFIG')

# ---------------
# 服务导出配置
# ---------------

# 默认容器内监听地址
CONTAINER_PORT = settings.get('CONTAINER_PORT', 5000)

# 服务相关插件配置
SERVICES_PLUGINS = settings.get('SERVICES_PLUGINS', default={})

# ---------------
# 资源命名配置
# ---------------

STR_APP_NAME = r'^([a-z0-9_-]){1,64}$'
STR_MODULE_NAME = r'^([a-z0-9_-]){1,16}$'
PROC_TYPE_PATTERN = r'^[a-z0-9]([-a-z0-9])*$'

# ---------------
# Redis 配置
# ---------------

# 与 apiserver 通信的 redis 管道, 需要确保两个项目中的配置一致
STREAM_CHANNEL_REDIS_URL = settings.get('STREAM_CHANNEL_REDIS_URL', default='redis://localhost:6379/0')

# 用于保存缓存等其他数据的 redis 服务器地址，未配置时使用 STREAM_CHANNEL_REDIS_URL 的值
REDIS_URL = settings.get('REDIS_URL', default=STREAM_CHANNEL_REDIS_URL)
# Redis sentinel 模式配置
SENTINEL_MASTER_NAME = settings.get('SENTINEL_MASTER_NAME', 'mymaster')
SENTINEL_PASSWORD = settings.get('SENTINEL_PASSWORD', '')

# Default connection options which have a shorter timeout and keepalive settings in order to make
# the connection more robust
REDIS_CONNECTION_OPTIONS = settings.get(
    'REDIS_CONNECTION_OPTIONS',
    {
        'socket_timeout': 3,
        'socket_connect_timeout': 3,
        'socket_keepalive': True,
        'socket_keepalive_options': get_default_keepalive_options(),
    },
)

# ---------------
# 后台任务 Celery 配置
# ---------------

CELERY_BROKER_URL = settings.get('CELERY_BROKER_URL', 'amqp://')
CELERY_RESULT_BACKEND = settings.get('CELERY_RESULT_BACKEND')

CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_IMPORTS = ["paas_wl.release_controller.builder.tasks", "paas_wl.resources.tasks"]
CELERY_BROKER_TRANSPORT_OPTIONS = settings.get('CELERY_BROKER_TRANSPORT_OPTIONS', {})

if not CELERY_BROKER_TRANSPORT_OPTIONS and is_redis_backend(CELERY_BROKER_URL):
    # Set redis connection timeout and keep-alive to lower values
    CELERY_BROKER_TRANSPORT_OPTIONS = copy.deepcopy(REDIS_CONNECTION_OPTIONS)
    if is_redis_sentinel_backend(CELERY_BROKER_URL):
        # 添加 sentinel 配置
        CELERY_BROKER_TRANSPORT_OPTIONS.update(
            {
                'master_name': settings.get('CELERY_BROKER_SENTINEL_MASTER_NAME', SENTINEL_MASTER_NAME),
                'sentinel_kwargs': {'password': settings.get('CELERY_BROKER_SENTINEL_PASSWORD', SENTINEL_PASSWORD)},
            }
        )

if is_redis_sentinel_backend(CELERY_RESULT_BACKEND):
    # 添加 sentinel 配置
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
        'master_name': settings.get('CELERY_RESULT_BACKEND_SENTINEL_MASTER_NAME', SENTINEL_MASTER_NAME),
        'sentinel_kwargs': {'password': settings.get('CELERY_RESULT_BACKEND_SENTINEL_PASSWORD', SENTINEL_PASSWORD)},
    }

CELERY_TASK_DEFAULT_QUEUE = settings.get("CELERY_TASK_DEFAULT_QUEUE", "celery")

# ---------------
# 资源限制配置
# ---------------
DEFAULT_WEB_REPLICAS_MAP = settings.get('DEFAULT_WEB_REPLICAS_MAP', {'stag': 1, 'prod': 2})

# 构建 pod 资源规格，按 k8s 格式书写
SLUGBUILDER_RESOURCES_SPEC = settings.get('SLUGBUILDER_RESOURCES_SPEC')

# ---------------
# 鉴权配置
# ---------------

# 用户类型，默认为蓝鲸用户
USER_TYPE = settings.get('USER_TYPE', ProviderType.BK.value)
# 转换为枚举类型
USER_TYPE = ProviderType(USER_TYPE)

BKAUTH_BACKEND_TYPE = settings.get('BKAUTH_BACKEND_TYPE', 'bk_token')
BKAUTH_TOKEN_APP_CODE = settings.get('BKAUTH_TOKEN_APP_CODE')
BKAUTH_TOKEN_SECRET_KEY = settings.get('BKAUTH_TOKEN_SECRET_KEY')

BKAUTH_BK_LOGIN_DOMAIN = settings.get('BKAUTH_BK_LOGIN_DOMAIN')
BKAUTH_BK_LOGIN_PATH = settings.get('BKAUTH_BK_LOGIN_PATH', '/')

# PaaS apiserver 服务地址
PAAS_APISERVER_ENDPOINT = settings.get('PAAS_APISERVER_ENDPOINT', 'http://bkpaas3-apiserver-web')


# 配置一个用于服务间鉴权的 JWT key，该配置可替代 INTERNAL_SERVICES_JWT_AUTH_CONF 和 PAAS_SERVICE_JWT_CLIENTS
# 当 PaaS 的所有服务都使用同一个 JWT key 时，可使用该配置项。
# ONE_SIMPLE_JWT_AUTH_KEY: your-key

# 微服务（后端引擎 API、增强服务 API）通用的默认 JWT 鉴权信息，用于请求其他服务
INTERNAL_SERVICES_JWT_AUTH_CONF = get_internal_services_jwt_auth_conf(settings)

# 用于校验内部服务间请求的 JWT 配置，携带用以下任何一个 key 签名的 JWT 的请求会被认为有效
PAAS_SERVICE_JWT_CLIENTS = get_paas_service_jwt_clients(settings)

# ---------------
# 部署环境相关
# ---------------
# 环境变量前缀
SYSTEM_CONFIG_VARS_KEY_PREFIX = settings.get('SYSTEM_CONFIG_VARS_KEY_PREFIX', 'BKPAAS_')

# 兼容内部旧的日志挂载配置
VOLUME_NAME_APP_LOGGING = settings.get('VOLUME_NAME_APP_LOGGING', 'applogs')
VOLUME_MOUNT_APP_LOGGING_DIR = settings.get('VOLUME_MOUNT_APP_LOGGING_DIR', '/app/logs')
VOLUME_HOST_PATH_APP_LOGGING_DIR = settings.get('VOLUME_HOST_PATH_APP_LOGGING_DIR', '/tmp/logs')

# 支持多模块的日志挂载配置
MUL_MODULE_VOLUME_NAME_APP_LOGGING = settings.get('MUL_MODULE_VOLUME_NAME_APP_LOGGING', 'appv3logs')
MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR = settings.get('MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR', '/app/v3logs')
MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR = settings.get(
    'MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR', '/tmp/v3logs'
)

# ---------------
# 调度集群相关
# ---------------

K8S_DEFAULT_CONNECT_TIMEOUT = 5
K8S_DEFAULT_READ_TIMEOUT = 60

# 指定 kubectl 使用的 config.yaml 文件路径，容器化交付时由 secret 挂载而来
KUBE_CONFIG_FILE = settings.get('KUBE_CONFIG_FILE', '/data/kubelet/conf/kubeconfig.yaml')

# 和 Deployment 资源回滚相关，设置值宜小，减轻 controller-manager 压力
MAX_RS_RETAIN = 3

# SLUG 最长存活时间
MAX_SLUG_SECONDS = 15 * 60

# 部署资源规则映射版本
GLOBAL_DEFAULT_MAPPER_VERSION = "v1"
LEGACY_MAPPER_VERSION = "v1"

# 默认读取 POD 最近日志行数
DEFAULT_POD_LOGS_LINE = 512

# ---------------
# 监控数据配置
# ---------------

# 对外暴露 metrics 的鉴权信息
METRIC_CLIENT_TOKEN_DICT = settings.get('METRIC_CLIENT_TOKEN_DICT', {})

# healthz: 将使用该 token 校验调用方身份
HEALTHZ_TOKEN = settings.get('HEALTHZ_TOKEN')

# 插件监控图表相关配置
MONITOR_CONFIG = settings.get('MONITOR_CONFIG', {})

# ---------------
# 多区域配置
# ---------------

# 所有可用区域的名字，用于初始化默认进程配置信息等
ALL_REGIONS = settings.get('ALL_REGIONS', ['default'])

# ---------------
# Ingress 配置
# ---------------

# 不指定则使用默认，可以指定为 bk-ingress-nginx
APP_INGRESS_CLASS = settings.get('APP_INGRESS_CLASS')

# ingress extensions/v1beta1 资源路径是否保留末尾斜杠
APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH = settings.get('APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH', True)

# 是否开启“现代” Ingress 资源序列化与反序列化逻辑，将产生以下影响：
#
# - 使用基于正则模式的 Ingress 路径与 Rewrite 规则
# - （**重要**）因为 rewrite 规则变更，不支持 <0.22.0 版本的 ingress-nginx
# - 增加 networking.k8s.io/v1beta1 和 networking.k8s.io/v1 版本的 Ingress 资源支持，当集群版本
#   支持对应 apiVersion 时启用
#
# 假如关闭此配置，可能有以下风险：
#
#  - 只能处理 extensions/v1beta1 版本的 Ingress 资源，如果未来的 Kubernetes 集群版本删除了对该
#    apiVersion 的支持，服务会报错
ENABLE_MODERN_INGRESS_SUPPORT = settings.get('ENABLE_MODERN_INGRESS_SUPPORT', True)

# 是否开启终端色彩
COLORFUL_TERMINAL_OUTPUT = True

# 应用独立域名相关配置
CUSTOM_DOMAIN_CONFIG = settings.get(
    'CUSTOM_DOMAIN_CONFIG',
    {
        "enabled": True,
        # 允许用户配置的独立域名后缀列表，如果为空列表，允许任意独立域名
        "valid_domain_suffixes": settings.get('VALID_CUSTOM_DOMAIN_SUFFIXES', []),
        # 是否允许用户修改独立域名相关配置，如果为 False，只能由管理员通过后台管理界面调整应用独立域名配置
        "allow_user_modifications": True,
    },
)

# -----------
# 进程相关配置
# -----------

# 默认进程规格套餐名称
DEFAULT_PROC_SPEC_PLAN = 'Starter'
PREMIUM_PROC_SPEC_PLAN = "4C2G5R"
ULTIMATE_PROC_SPEC_PLAN = "4C4G5R"

# 默认进程规格套餐配置
# 最大资源限制，格式与单位请参考：https://kubernetes.io/docs/concepts/policy/resource-quotas/
DEFAULT_PROC_SPEC_PLANS = {
    "Starter": {
        'max_replicas': 5,
        'limits': {'cpu': '4096m', 'memory': '1024Mi'},
        'requests': {'cpu': '100m', 'memory': '64Mi'},
    },
    "4C1G5R": {
        'max_replicas': 5,
        'limits': {'cpu': '4096m', 'memory': '1024Mi'},
        'requests': {'cpu': '100m', 'memory': '64Mi'},
    },
    "4C2G5R": {
        'max_replicas': 5,
        'limits': {'cpu': '4096m', 'memory': '2048Mi'},
        'requests': {'cpu': '100m', 'memory': '64Mi'},
    },
    "4C4G5R": {
        'max_replicas': 5,
        'limits': {'cpu': '4096m', 'memory': '4096Mi'},
        'requests': {'cpu': '100m', 'memory': '64Mi'},
    },
}

# 按照进程名称与环境，配置默认副本数
ENGINE_PROC_REPLICAS_BY_TYPE = {
    # （进程类型, 环境名称）： 副本数量
    ('web', 'stag'): 1,
    ('web', 'prod'): 2,
}


# ---------------------------------------------
# （internal）内部配置，仅开发项目与特殊环境下使用
# ---------------------------------------------

FOR_TESTS_DEFAULT_REGION = settings.get('FOR_TESTS_DEFAULT_REGION', 'default')

FOR_TESTS_APISERVER_URL = settings.get('FOR_TESTS_APISERVER_URL', 'http://localhost:28080')
FOR_TESTS_CA_DATA = settings.get('FOR_TESTS_CA_DATA', '')
FOR_TESTS_CERT_DATA = settings.get('FOR_TESTS_CERT_DATA', '')
FOR_TESTS_KEY_DATA = settings.get('FOR_TESTS_KEY_DATA', '')
FOR_TESTS_FORCE_DOMAIN = settings.get('FOR_TESTS_FORCE_DOMAIN', '')

FOR_TESTS_CLUSTER_CONFIG = {
    "url": FOR_TESTS_APISERVER_URL,
    "ca_data": FOR_TESTS_CA_DATA,
    "cert_data": FOR_TESTS_CERT_DATA,
    "key_data": FOR_TESTS_KEY_DATA,
    "force_domain": FOR_TESTS_FORCE_DOMAIN,
}

# 调用蓝鲸 API 的鉴权信息
BK_APP_CODE = settings.get('BK_APP_CODE', '')
BK_APP_SECRET = settings.get('BK_APP_SECRET', '')

# Sentry 错误收集服务配置
SENTRY_CONFIG = settings.get('SENTRY_CONFIG', {})

# request.META 中 request_id 的键
REQUEST_ID_META_KEY = 'HTTP_X_REQUEST_ID'
# headers 中 request_id 的键
REQUEST_ID_HEADER_KEY = 'X-Request-Id'

# openTelemetry trace 配置，默认不启用
ENABLE_OTEL_TRACE = settings.get('ENABLE_OTEL_TRACE', False)
OTEL_INSTRUMENT_DB_API = settings.get('OTEL_INSTRUMENT_DB_API', True)
# 上报数据服务名称
OTEL_SERVICE_NAME = settings.get('OTEL_SERVICE_NAME', 'bkpaas3-workloads')
# sdk 采样规则（always_on / always_off / parentbased_always_on...）
OTEL_SAMPLER = settings.get('OTEL_SAMPLER', 'always_on')
OTEL_BK_DATA_TOKEN = settings.get('OTEL_BK_DATA_TOKEN', '')
OTEL_GRPC_URL = settings.get('OTEL_GRPC_URL', '')

if ENABLE_OTEL_TRACE:
    INSTALLED_APPS += ('paas_wl.tracing',)

# 蓝鲸监控相关配置
# 是否下发 ServiceMonitor 的总开关
BKMONITOR_ENABLED = settings.get("BKMONITOR_ENABLED", False)
# 蓝鲸监控运维相关的额外配置
BKMONITOR_METRIC_RELABELINGS = settings.get("BKMONITOR_METRIC_RELABELINGS", [])

# 网关运行环境
APIGW_ENVIRONMENT = settings.get('APIGW_ENVIRONMENT', 'prod')
# 网关前缀 URL 模板
BK_API_URL_TMPL = settings.get('BK_API_URL_TMPL', 'http://localhost:8080/api/{api_name}/')
