# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
# type: ignore
"""PaaS apiserver service settings

默认情况下，本项目会读取根目录（manage.py 所在目录）下的 `settings_files` 子目录内的所有
YAML 文件和 `settings_local.yaml` 的内容，将其作为配置项使用。你也可以用 `PAAS_SETTINGS`
环境变量指定其他配置文件，比如：

    # 多个配置文件使用 ; 分割
    export PAAS_SETTINGS='common.yaml;dev.yaml'

指定其他文件后，`settings_files/*.yaml` 与 `settings_local.yaml` 仍然会生效，最终
配置会是所有内容合并后的结果。

除了 YAML 外，每个配置项也可通过环境变量设置。比如，在 YAML 文件里的配置项 `SECRET_KEY: foo`，
也可使用以下环境变量修改：

    export PAAS_SECRET_KEY="foo"

注意事项：

- 必须添加 `PAAS_` 前缀
- 环境变量比 YAML 配置的优先级更高
- 环境变量可修改字典内的嵌套值，参考文档：https://www.dynaconf.com/envvars/
"""
import copy
import os
import sys
from pathlib import Path
from typing import Dict, List

from bkpaas_auth.core.constants import ProviderType
from django.contrib import messages
from django.utils.encoding import force_bytes, force_str
from dynaconf import LazySettings, Validator
from environ import Env

from .utils import (
    get_database_conf,
    get_default_keepalive_options,
    get_paas_service_jwt_clients,
    get_service_remote_endpoints,
    is_redis_backend,
    is_redis_sentinel_backend,
)

BASE_DIR = Path(__file__).parents[2]

SETTINGS_FILES_GLOB = str(BASE_DIR / 'settings_files/*.yaml')
LOCAL_SETTINGS = str(BASE_DIR / 'settings_local.yaml')

settings = LazySettings(
    environments=False,
    load_dotenv=True,
    includes=[SETTINGS_FILES_GLOB, LOCAL_SETTINGS],
    validators=[
        # Configure minimal required settings
        Validator('BKKRILL_ENCRYPT_SECRET_KEY', must_exist=True),
    ],
    # Envvar name configs
    ENVVAR_PREFIX_FOR_DYNACONF="PAAS",
    ENVVAR_FOR_DYNACONF="PAAS_SETTINGS",
)

_notset = object()

# 蓝鲸数据库内容加密私钥
# 使用 `from cryptography.fernet import Fernet; Fernet.generate_key()` 生成随机秘钥
# 详情查看：https://cryptography.io/en/latest/fernet/
BKKRILL_ENCRYPT_SECRET_KEY = force_bytes(settings.get('BKKRILL_ENCRYPT_SECRET_KEY', ''))

# Django 项目使用的 SECRET_KEY，如未配置，使用 BKKRILL 的 secret key 替代
SECRET_KEY = settings.get("SECRET_KEY") or force_str(BKKRILL_ENCRYPT_SECRET_KEY)

DEBUG = settings.get('DEBUG', False)

SESSION_COOKIE_HTTPONLY = False

RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.argv[0] or "PYTEST_XDIST_TESTRUNUID" in os.environ

INSTALLED_APPS = [
    # WARNING: never enable django.contrib.admin here
    # Enable auth and contenttypes but don't migrate tables
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',
    'bootstrap3',
    'corsheaders',
    'webpack_loader',
    'django_prometheus',
    'paasng.platform.feature_flags',
    'paasng.accounts',
    'paasng.platform.applications',
    'paasng.platform.log',
    'paasng.platform.modules',
    'paasng.platform.oauth2',
    'paasng.platform.operations',
    'paasng.platform.environments',
    'paasng.ci',
    'paasng.cnative',
    'paasng.engine',
    'paasng.engine.streaming',
    'paasng.publish.market',
    'paasng.publish.sync_market',
    'paasng.publish.entrance',
    'paasng.dev_resources.sourcectl',
    'paasng.dev_resources.servicehub',
    'paasng.dev_resources.services',
    'paasng.dev_resources.templates',
    'paasng.plat_admin.api_doc',
    'paasng.plat_admin.admin42',
    'paasng.plat_admin.system',
    'paasng.monitoring.monitor',
    'paasng.monitoring.healthz',
    'paasng.accessories.search',
    'paasng.accessories.smart_advisor',
    'paasng.accessories.bk_lesscode',
    'paasng.accessories.iam.bkpaas_iam_migration',
    'paasng.accessories.iam.members',
    'paasng.extensions.declarative',
    'paasng.extensions.scene_app',
    'paasng.extensions.smart_app',
    'paasng.extensions.bk_plugins',
    'paasng.pluginscenter',
    'paasng.pluginscenter.iam_adaptor',
    'paasng.platform.mgrlegacy',
    'bkpaas_auth',
    'apigw_manager.apigw',
    'paasng.plat_admin.initialization',
    # Put "scheduler" in the last position so models in other apps can be ready
    'paasng.platform.scheduler',
    'revproxy',
    # workloads apps
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

# Allow extending installed apps
EXTRA_INSTALLED_APPS = settings.get('EXTRA_INSTALLED_APPS', [])
INSTALLED_APPS += EXTRA_INSTALLED_APPS

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'paasng.accounts.middlewares.RequestIDProvider',  # 注入 RequestID
    'paasng.utils.api_middleware.ApiLogMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'paasng.utils.middlewares.WhiteNoiseRespectPrefixMiddleware',
    'bkpaas_auth.middlewares.CookieLoginMiddleware',
    'paasng.accounts.middlewares.SiteAccessControlMiddleware',
    'paasng.accounts.middlewares.PrivateTokenAuthenticationMiddleware',
    # API Gateway related
    'apigw_manager.apigw.authentication.ApiGatewayJWTGenericMiddleware',  # JWT 认证
    'apigw_manager.apigw.authentication.ApiGatewayJWTAppMiddleware',  # JWT 透传的应用信息
    'apigw_manager.apigw.authentication.ApiGatewayJWTUserMiddleware',  # JWT 透传的用户信息
    # Must placed below `ApiGatewayJWTAppMiddleware` because it depends on `request.app`
    'paasng.accounts.middlewares.AuthenticatedAppAsUserMiddleware',
    # Internal service authentication related
    'blue_krill.auth.client.VerifiedClientMiddleware',
    'paasng.accounts.internal.user.SysUserFromVerifiedClientMiddleware',
    # Other utilities middlewares
    'paasng.utils.middlewares.AutoDisableCSRFMiddleware',
    'paasng.utils.middlewares.APILanguageMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# 管理者用户：拥有全量应用权限（经权限中心鉴权）
ADMIN_USERNAME = settings.get('ADMIN_USERNAME', 'admin')

AUTH_USER_MODEL = 'bkpaas_auth.User'

AUTHENTICATION_BACKENDS = ['bkpaas_auth.backends.UniversalAuthBackend', 'bkpaas_auth.backends.APIGatewayAuthBackend']

# FIXME: Enable this will cause 500 Error, will fix later
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = 'paasng.urls'

# 从 request.META 读取 request_id 的键
REQUEST_ID_META_KEY = 'HTTP_X_REQUEST_ID'
# 发起请求时，将 request_id 设置在 headers 中的键
REQUEST_ID_HEADER_KEY = 'X-Request-Id'

WSGI_APPLICATION = 'paasng.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'zh-cn'
LANGUAGES = (
    ("zh-cn", "简体中文"),
    ("en", "English"),
)
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 国际化 cookie 信息必须跟整个蓝鲸体系保存一致
LANGUAGE_COOKIE_NAME = "blueking_language"
LANGUAGE_COOKIE_PATH = "/"
# 国际化 cookie 默认写在整个蓝鲸的根域下
LANGUAGE_COOKIE_DOMAIN = settings.get('BK_COOKIE_DOMAIN')

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

CHANGELOG_PATH = os.path.join(BASE_DIR, 'changelog')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
SITE_URL = '/'
STATIC_ROOT = str(BASE_DIR / 'public' / 'static')

STATIC_URL = settings.get('STATIC_URL', '/static/')

STATICFILES_DIRS = (
    # Staticfile path generated by webpack
    str(BASE_DIR / 'public' / 'assets'),
)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'bundles/',
        'STATS_FILE': str(BASE_DIR / 'public' / 'webpack-stats.json'),
    }
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    # the context to the templates
    'django.contrib.auth.context_processors.auth',
    'django.template.context_processors.request',
    'django.template.context_processors.csrf',
    'django.template.context_processors.i18n',
    'paasng.plat_admin.admin42.context_processors.admin_config',
)

TEMPLATE_DIRS = [str(BASE_DIR / 'templates')]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': list(TEMPLATE_DIRS),
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': list(TEMPLATE_CONTEXT_PROCESSORS),
        },
    },
]

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'paasng.utils.views.custom_exception_handler',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework.authentication.SessionAuthentication',),
    'DATETIME_FORMAT': "%Y-%m-%d %H:%M:%S",
    # TIPS: 覆盖 SearchFilter、OrderingFilter 的过滤参数，与应用列表保持用同样的搜索、排序字段
    'SEARCH_PARAM': 'search_term',
    'ORDERING_PARAM': 'order_by',
    # 增加为蓝鲸 API 规范设计的 Renderer
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        # 可将 Response 转换为蓝鲸 API 规范所规定的格式： {"result": true, "message": "error", ...}
        'paasng.utils.views.BkStandardApiJSONRenderer',
    ],
}

# 自定义 drf-yasg 配置
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'paasng.plat_admin.api_doc.extended_auto_schema.ExtendedSwaggerAutoSchema',
    'DEFAULT_GENERATOR_CLASS': 'paasng.plat_admin.api_doc.generators.OpenAPISchemaGenerator',
}

MESSAGE_TAGS = {messages.ERROR: 'danger'}

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
    'filters': {
        'request_id': {'()': 'paasng.utils.logging.RequestIDFilter'},
    },
    'handlers': {
        'null': {'level': LOG_LEVEL, 'class': 'logging.NullHandler'},
        'mail_admins': {'level': LOG_LEVEL, 'class': 'django.utils.log.AdminEmailHandler'},
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
        'logstash_redis': _redis_handler,
    },
    'root': {'handlers': _default_handlers, 'level': LOG_LEVEL, 'propagate': False},
    'loggers': {
        'django': {'handlers': ['null'], 'level': LOG_LEVEL, 'propagate': False},
        'django.request': {'handlers': _default_handlers, 'level': 'ERROR', 'propagate': False},
        'django.security': {'level': 'INFO'},
        # 常用模块日志级别
        'paasng': {'level': 'NOTSET'},
        'commands': {'handlers': _default_handlers, 'level': LOG_LEVEL, 'propagate': False},
        # 设置第三方模块日志级别，避免日志过多
        'bkpaas_auth': {'level': 'WARNING'},
        'apscheduler': {'level': 'WARNING'},
        'requests': {'level': 'ERROR'},
        "urllib3.connectionpool": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "boto3": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "botocore": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "console": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "iam": {"level": settings.get('IAM_LOG_LEVEL', "ERROR"), "handlers": _default_handlers, "propagate": False},
    },
}

if settings.get('LOGGING_ENABLE_SQL_QUERIES', False):
    LOGGING['loggers']['django.db.backends'] = {  # type: ignore
        'handlers': _default_handlers,
        'level': LOG_LEVEL,
        'propagate': True,
    }


# 通知插件
NOTIFICATION_PLUGIN_CLASSES = settings.get(
    'NOTIFICATION_PLUGIN_CLASSES',
    {
        "mail": "paasng.utils.notification_plugins.MailNotificationPlugin",
        "sms": "paasng.utils.notification_plugins.SMSNotificationPlugin",
        "wechat": "paasng.utils.notification_plugins.WeChatNotificationPlugin",
    },
)


# ------------------------
# Django 基础配置（自定义）
# ------------------------

DATABASES = {
    "default": get_database_conf(settings),
    "workloads": get_database_conf(settings, encrypted_url_var="WL_DATABASE_URL", env_var_prefix="WL_"),
}
DATABASE_ROUTERS = ["paasng.platform.core.storages.dbrouter.WorkloadsDBRouter"]

# == Redis 相关配置项，该 Redis 服务将被用于：缓存

# Redis 服务地址
REDIS_URL = settings.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
# Redis sentinel 模式配置
SENTINEL_MASTER_NAME = settings.get('SENTINEL_MASTER_NAME', 'mymaster')
SENTINEL_PASSWORD = settings.get('SENTINEL_PASSWORD', '')

# 修改 Redis 连接时的 keepalive 配置，让连接更健壮
REDIS_CONNECTION_OPTIONS = {
    'socket_timeout': 3,
    'socket_connect_timeout': 3,
    'socket_keepalive': True,
    'socket_keepalive_options': get_default_keepalive_options(),
}

# == 缓存相关配置项
# DEFAULT_CACHE_CONFIG 优先级最高，若无该配置则检查是否配置 Redis，若存在则作为缓存，否则使用临时文件作为缓存
DEFAULT_CACHE_CONFIG = settings.get('DEFAULT_CACHE_CONFIG')
if DEFAULT_CACHE_CONFIG:
    CACHES = {'default': DEFAULT_CACHE_CONFIG}
elif REDIS_URL:
    CACHES = {'default': Env.cache_url_config(REDIS_URL)}
else:
    CACHES = {
        'default': {'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache', 'LOCATION': '/tmp/django_cache'}
    }

# 修改默认 Cookie 名称，避免冲突
SESSION_COOKIE_NAME = 'bk_paas3_sessionid'
CSRF_COOKIE_NAME = 'bk_paas3_csrftoken'

FORCE_SCRIPT_NAME = settings.get('FORCE_SCRIPT_NAME')
CSRF_COOKIE_DOMAIN = settings.get('CSRF_COOKIE_DOMAIN')
SESSION_COOKIE_DOMAIN = settings.get('SESSION_COOKIE_DOMAIN')

# 蓝鲸登录票据在Cookie中的名称，权限中心 API 未接入 APIGW，访问时需要提供登录态信息
BK_COOKIE_NAME = settings.get('BK_COOKIE_NAME', "bk_token")

# 允许通过什么域名访问服务，详见：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#allowed-hosts
ALLOWED_HOSTS = settings.get('ALLOWED_HOSTS', ['*'])

# == CORS 请求跨域相关配置
#
# CORS 允许的来源
CORS_ORIGIN_REGEX_WHITELIST = settings.get('CORS_ORIGIN_REGEX_WHITELIST', [])

CORS_ORIGIN_ALLOW_ALL = settings.get('CORS_ORIGIN_ALLOW_ALL', False)

# 默认允许通过通过跨域请求传递 Cookie，默认允许
CORS_ALLOW_CREDENTIALS = True

# == Celery 相关配置

CELERY_BROKER_URL = settings.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = settings.get('CELERY_RESULT_BACKEND', REDIS_URL)

if settings.get('CELERY_BROKER_HEARTBEAT', _notset) != _notset:
    CELERY_BROKER_HEARTBEAT = settings.get('CELERY_BROKER_HEARTBEAT')

# Celery 格式 / 时区相关配置
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_ENABLE_UTC = False

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

# Celery 队列名称
CELERY_TASK_DEFAULT_QUEUE = os.environ.get("CELERY_TASK_DEFAULT_QUEUE", "celery")


# --------
# 系统配置
# --------

# 调用蓝鲸 API 的鉴权信息（BK_APP_CODE 用固定值）
BK_APP_CODE = settings.get('BK_APP_CODE', 'bk_paas3')
BK_APP_SECRET = settings.get('BK_APP_SECRET', '')

# PaaS 2.0 在权限中心注册的系统ID （并非是平台的 Code）
IAM_SYSTEM_ID = settings.get('IAM_SYSTEM_ID', default='bk_paas')

# PaaS 3.0 在权限中心注册的系统 ID
IAM_PAAS_V3_SYSTEM_ID = settings.get('IAM_PAAS_V3_SYSTEM_ID', default='bk_paas3')

# 请求权限中心的鉴权信息
IAM_APP_CODE = settings.get('IAM_APP_CODE', default=BK_APP_CODE)
IAM_APP_SECRET = settings.get('IAM_APP_SECRET', default=BK_APP_SECRET)

# 额外指定的用于存储 migration 文件的 APP
# https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md#21-django-migration
BK_IAM_MIGRATION_APP_NAME = "bkpaas_iam_migration"

# 跳过初始化已有应用数据到权限中心（注意：仅跳过初始化数据，所有权限相关的操作还是依赖权限中心）
BK_IAM_SKIP = settings.get('BK_IAM_SKIP', False)

BKAUTH_DEFAULT_PROVIDER_TYPE = settings.get('BKAUTH_DEFAULT_PROVIDER_TYPE', 'BK')

# 蓝鲸的云 API 地址，用于内置环境变量的配置项
BK_COMPONENT_API_URL = settings.get('BK_COMPONENT_API_URL', '')
# 蓝鲸的组件 API 地址，网关 SDK 依赖该配置项（该项值与 BK_COMPONENT_API_URL 一致）
COMPONENT_SYSTEM_HOST = settings.get('COMPONENT_SYSTEM_HOST', BK_COMPONENT_API_URL)
# 蓝鲸的组件 API 测试环境地址
COMPONENT_SYSTEM_HOST_IN_TEST = settings.get('COMPONENT_SYSTEM_HOST_IN_TEST', 'http://localhost:8080')
# APIGW-Dashboard 接口地址
APIGW_DASHBOARD_HOST = settings.get('APIGW_DASHBOARD_URL', 'http://localhost:8080')

BK_APIGW_NAME = settings.get('BK_APIGW_NAME')
# 网关运行环境
# TODO BK_LESSCODE_APIGW_STAGE 和 BK_IAM_APIGW_SERVICE_STAGE 考虑复用 APIGW_ENVIRONMENT?
APIGW_ENVIRONMENT = settings.get('APIGW_ENVIRONMENT', 'prod')
# 网关 API 访问地址模板
BK_API_URL_TMPL = settings.get('BK_API_URL_TMPL', 'http://localhost:8080/api/{api_name}/')

# 开发者中心 region 与 APIGW user_auth_type 的对应关系
REGION_TO_USER_AUTH_TYPE_MAP = settings.get('REGION_TO_USER_AUTH_TYPE_MAP', {'default': 'default'})

# 提供 metrics 接口用的 client token 列表
METRIC_CLIENT_TOKEN_DICT = settings.get('METRIC_CLIENT_TOKEN_DICT', {})

# 是否默认允许创建 Smart 应用
IS_ALLOW_CREATE_SMART_APP_BY_DEFAULT = settings.get('IS_ALLOW_CREATE_SMART_APP_BY_DEFAULT', True)

# 是否默认允许创建云原生应用
IS_ALLOW_CREATE_CLOUD_NATIVE_APP_BY_DEFAULT = settings.get('IS_ALLOW_CREATE_CLOUD_NATIVE_APP_BY_DEFAULT', False)

# 云原生应用的默认集群名称
CLOUD_NATIVE_APP_DEFAULT_CLUSTER = settings.get("CLOUD_NATIVE_APP_DEFAULT_CLUSTER", "")

# ---------------
# HealthZ 配置
# ---------------

# healthz: 将使用该 token 校验调用方身份，必须设置为有效字符串后方能生效
HEALTHZ_TOKEN = settings.get('HEALTHZ_TOKEN')

# 已启用探针列表
# 参照 paasng.monitoring.healthz.probes 中包含的探针配置
HEALTHZ_PROBES = settings.get(
    'HEALTHZ_PROBES',
    [
        'paasng.monitoring.healthz.probes.PlatformMysqlProbe',
        'paasng.monitoring.healthz.probes.PlatformRedisProbe',
        'paasng.monitoring.healthz.probes.ServiceHubProbe',
        'paasng.monitoring.healthz.probes.PlatformBlobStoreProbe',
        'paasng.monitoring.healthz.probes.BKIAMProbe',
    ],
)

# 蓝鲸的组件 API 的 Healthz 地址
COMPONENT_SYSTEM_HEALTHZ_URL = settings.get('COMPONENT_SYSTEM_HEALTHZ_URL', 'http://localhost:8080')
# API 网关的 Healthz 地址
APIGW_HEALTHZ_URL = settings.get('APIGW_HEALTHZ_URL', 'http://localhost:8080')

# ---------------
# 平台基础功能配置
# ---------------

# 是否自动创建用户，默认打开，关闭后新用户将无法访问
AUTO_CREATE_REGULAR_USER = settings.get('AUTO_CREATE_REGULAR_USER', True)

# 每个应用下最多创建的模块数量
MAX_MODULES_COUNT_PER_APPLICATION = settings.get('MAX_MODULES_COUNT_PER_APPLICATION', 10)

PAAS_LEGACY_DBCONF = get_database_conf(
    settings, encrypted_url_var='PAAS_LEGACY_DATABASE_URL', env_var_prefix='PAAS_LEGACY_', for_tests=RUNNING_TESTS
)

# 旧版本 PaaS 数据库，敏感字段所使用的加密 key
PAAS_LEGACY_DB_ENCRYPT_KEY = settings.get('PAAS_LEGACY_DB_ENCRYPT_KEY')

# ---------------
# 对象存储配置
# ---------------

BLOBSTORE_TYPE = settings.get('BLOBSTORE_TYPE')

# 应用构件包所使用对象存储配置
BLOBSTORE_S3_ENDPOINT = settings.get('BLOBSTORE_S3_ENDPOINT', default='http://127.0.0.1:9100')
BLOBSTORE_S3_ACCESS_KEY = settings.get('BLOBSTORE_S3_ACCESS_KEY', default='minio')
BLOBSTORE_S3_SECRET_KEY = settings.get('BLOBSTORE_S3_SECRET_KEY', default='')

# 对象存储 SDK 额外配置项，使用 minio 服务必须启用该配置
BLOBSTORE_S3_REGION_NAME = settings.get('BLOBSTORE_S3_REGION_NAME', 'us-east-1')
BLOBSTORE_S3_SIG_VERSION = settings.get('BLOBSTORE_S3_SIG_VERSION', 's3v4')

# 用于存储 Logo 图片，默认与 BlobStore 使用相同配置
RGW_ENDPOINT_URL = settings.get('RGW_ENDPOINT_URL', default=BLOBSTORE_S3_ENDPOINT)
RGW_ACCESS_KEY_ID = settings.get('RGW_ACCESS_KEY_ID', default=BLOBSTORE_S3_ACCESS_KEY)
RGW_SECRET_ACCESS_KEY = settings.get('RGW_SECRET_ACCESS_KEY', default=BLOBSTORE_S3_SECRET_KEY)
RGW_STORAGE_BUCKET_NAME = 'app-logo'

# 当配置该项时，使用 BK-Repo 而不是 S3 作为 BlobStore 存储
BLOBSTORE_BKREPO_CONFIG = settings.get('BLOBSTORE_BKREPO_CONFIG')

# 增强服务 LOGO bucket
SERVICE_LOGO_BUCKET = settings.get('SERVICE_LOGO_BUCKET', 'bkpaas3-platform-assets')
# 应用 Logo 存储 bucket 名称
APP_LOGO_BUCKET = settings.get('APP_LOGO_BUCKET', 'bkpaas3-apps-logo')
# 应用 Logo 缓存时间设置
APP_LOGO_MAX_AGE = str(30 * 24 * 3600)
# 插件 Logo 存储 bucket 名称
PLUGIN_LOGO_BUCKET = settings.get('PLUGIN_LOGO_BUCKET', 'bkpaas3-plugin-logo')
# 插件 Logo 缓存时间设置
PLUGIN_LOGO_MAX_AGE = str(30 * 24 * 3600)

# 蓝鲸PaaS平台访问地址，用于平台访问链接拼接与内置环境变量的配置项
BKPAAS_URL = settings.get('BKPAAS_URL', '')

# 蓝鲸 PaaS2.0 平台访问地址，用于平台访问链接拼接与内置环境变量的配置项
BK_PAAS2_URL = settings.get('BK_PAAS2_URL', '')

# 蓝鲸 PaaS2.0 平台内网访问地址，用于内置环境变量的配置项
BK_PAAS2_INNER_URL = settings.get('BK_PAAS2_INNER_URL', BK_PAAS2_URL)

# 应用默认 Logo 图片地址
APPLICATION_DEFAULT_LOGO = settings.get('APPLICATION_DEFAULT_LOGO', f'{BKPAAS_URL}/static/images/default_logo.png')

# 插件应用默认 Logo 图片地址
PLUGIN_APP_DEFAULT_LOGO = settings.get('PLUGIN_APP_DEFAULT_LOGO', APPLICATION_DEFAULT_LOGO)

# 蓝鲸 SSM 平台访问地址, 用于 access_token 验证
BK_SSM_URL = settings.get('BK_SSM_URL', '')

# 权限中心内网访问地址，用于对接权限中心
BK_IAM_V3_INNER_URL = settings.get('BK_IAM_V3_INNER_URL', 'http://localhost:8080')

# 访问的权限中心 APIGW 版本
BK_IAM_APIGW_SERVICE_STAGE = settings.get('BK_IAM_APIGW_SERVICE_STAGE', 'stage')

# 参数说明 https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md#22-config
# 如果通过网关访问, BK_IAM_APIGATEWAY_URL 将替代 BK_IAM_V3_INNER_URL
BK_IAM_USE_APIGATEWAY = settings.get('BK_IAM_USE_APIGATEWAY', True)

BK_IAM_APIGATEWAY_URL = settings.get(
    'BK_IAM_APIGATEWAY_URL', f"{BK_API_URL_TMPL.format(api_name='bk-iam')}/{BK_IAM_APIGW_SERVICE_STAGE}"
)

# 权限中心回调地址（provider api）
# 会存在开发者中心访问地址是 https 协议，但是 API 只能用 http 协议的情况，所以不能直接用 BKPAAS_URL
# ITSM 回调地址也复用了这个变量，修改变量名会涉及到 helm values 等多个地方同时修改，暂时先保留这个变量名
BK_IAM_RESOURCE_API_HOST = settings.get('BK_IAM_RESOURCE_API_HOST', BKPAAS_URL)

# 权限中心应用ID，用于拼接权限中心的在桌面的访问地址
BK_IAM_V3_APP_CODE = "bk_iam"


# 蓝鲸平台体系的地址，用于内置环境变量的配置项
BK_CC_URL = settings.get('BK_CC_URL', '')
BK_JOB_URL = settings.get('BK_JOB_URL', '')
BK_IAM_URL = settings.get('BK_IAM_URL', '')
BK_USER_URL = settings.get('BK_USER_URL', '')
BK_MONITORV3_URL = settings.get('BK_MONITORV3_URL', '')
BK_LOG_URL = settings.get('BK_LOG_URL', '')
BK_REPO_URL = settings.get('BK_REPO_URL', '')
BK_CI_URL = settings.get('BK_CI_URL', '')
BK_CODECC_URL = settings.get('BK_CODECC_URL', '')
BK_TURBO_URL = settings.get('BK_TURBO_URL', '')
BK_PIPELINE_URL = settings.get('BK_PIPELINE_URL', '')

BK_PLATFORM_URLS = settings.get(
    'BK_PLATFORM_URLS',
    {
        # 旧版 IAM 地址，目前已废弃
        'BK_IAM_INNER_HOST': settings.get('BK_IAM_INNER_URL', 'http://:'),
        'BK_IAM_V3_APP_CODE': settings.get('BK_IAM_V3_APP_CODE', 'bk_iam'),
        'BK_IAM_V3_INNER_HOST': BK_IAM_V3_INNER_URL,
        'BK_CC_HOST': BK_CC_URL,
        'BK_JOB_HOST': BK_JOB_URL,
    },
)

# 权限中心用户组申请链接
BK_IAM_USER_GROUP_APPLY_TMPL = BK_IAM_URL + "/apply-join-user-group?id={user_group_id}"

# 应用移动端访问地址，用于渲染模板与内置环境变量的配置项
BKPAAS_WEIXIN_URL_MAP = settings.get(
    'BKPAAS_WEIXIN_URL_MAP',
    {
        'stag': 'http://localhost:8080/',
        'prod': 'http://localhost:8080/',
    },
)
# 应用移动端允许的域名后缀，如果为空列表，允许任意域名
MOBILE_DOAMIN_SUFFIXS = settings.get('MOBILE_DOAMIN_SUFFIXS', ['.example.com'])

# 统一登录页面地址，用于模板渲染与内置环境变量的配置项
LOGIN_FULL = settings.get('LOGIN_FULL', f'{BK_PAAS2_URL}/login/')
LOGIN_SIMPLE = settings.get('LOGIN_SIMPLE', f'{BK_PAAS2_URL}/login/plain/')

# 蓝鲸统一登录服务地址，用于平台登录
BK_LOGIN_API_URL = settings.get('BK_LOGIN_API_URL', LOGIN_FULL)

# 蓝鲸桌面访问地址，用于内置环境变量
BK_CONSOLE_URL = settings.get('BK_CONSOLE_URL', f'{BK_PAAS2_URL}/console/')

# 用于测试的无意义的应用 template 名称
DUMMY_TEMPLATE_NAME = 'dummy_template'

# 默认 Region 名称
DEFAULT_REGION_NAME = settings.get('DEFAULT_REGION_NAME', 'default')

DEFAULT_REGION_TEMPLATE = {
    "name": "default",
    "display_name": "默认版",
    "basic_info": {
        "description": "默认版",
        "link_production_app": BK_CONSOLE_URL + "?app={code}",
        "link_engine_app": "http://example.com/{region}-{name}/",
        "extra_logo_bucket_info": {},
        "deploy_ver_for_update_svn_account": "default",
        "legacy_deploy_version": "default",
        "built_in_config_var": {
            "LOGIN_URL": {
                "stag": LOGIN_FULL,
                "prod": LOGIN_FULL,
            },
            "REMOTE_STATIC_URL": {
                "stag": "http://example.com/static_api/",
                "prod": "http://example.com/static_api/",
            },
        },
    },
    "entrance_config": {
        # - 1: 子路径模式
        # - 2: 子域名模式
        "exposed_url_type": 1,
        "manually_upgrade_to_subdomain_allowed": False,
    },
    "mul_modules_config": {"creation_allowed": True},
    "enabled_feature_flags": [],
    # 应用是否需要写入蓝鲸体系其他系统访问地址的环境变量
    "provide_env_vars_platform": True,
    # 是否允许部署“蓝鲸可视化开发平台提供源码包”
    "allow_deploy_app_by_lesscode": True,
}

REGION_CONFIGS = settings.get('REGION_CONFIGS', {'regions': [copy.deepcopy(DEFAULT_REGION_TEMPLATE)]})

# 蓝鲸 OAuth 服务地址（用于纳管蓝鲸应用 bk_app_code/bk_app_secret/）
ENABLE_BK_OAUTH = settings.get('ENABLE_BK_OAUTH', False)
BK_OAUTH_API_URL = settings.get('BK_OAUTH_API_URL', "http://localhost:8080")

# --------
# 用户鉴权模块 bkpaas_auth SDK 相关配置
# --------
# 解析通过 API Gateway 的请求，该值为空时跳过解析
APIGW_PUBLIC_KEY = settings.get('APIGW_PUBLIC_KEY', '')

BKAUTH_BACKEND_TYPE = settings.get('BKAUTH_BACKEND_TYPE', 'bk_token')
BKAUTH_TOKEN_APP_CODE = settings.get('BKAUTH_TOKEN_APP_CODE', BK_APP_CODE)
BKAUTH_TOKEN_SECRET_KEY = settings.get('BKAUTH_TOKEN_SECRET_KEY', BK_APP_SECRET)

BKAUTH_USER_COOKIE_VERIFY_URL = settings.get('BKAUTH_USER_COOKIE_VERIFY_URL', f"{BK_LOGIN_API_URL}/api/v3/is_login/")
BKAUTH_TOKEN_USER_INFO_ENDPOINT = settings.get(
    'BKAUTH_TOKEN_USER_INFO_ENDPOINT', f'{BK_COMPONENT_API_URL}/api/c/compapi/v2/bk_login/get_user/'
)
BKAUTH_TOKEN_GRANT_ENDPOINT = settings.get('BKAUTH_TOKEN_GRANT_ENDPOINT')
BKAUTH_TOKEN_CHECK_ENDPOINT = settings.get('BKAUTH_TOKEN_CHECK_ENDPOINT')
BKAUTH_BK_LOGIN_DOMAIN = settings.get('BKAUTH_BK_LOGIN_DOMAIN')
BKAUTH_BK_LOGIN_PATH = settings.get('BKAUTH_BK_LOGIN_PATH', '/')

# [admin] 管理后台页面的人员选择器的数据接口地址
USER_SELECTOR_LIST_API = f'{BK_COMPONENT_API_URL}/api/c/compapi/v2/usermanage/fs_list_users/'

# 用户类型，默认为蓝鲸用户
USER_TYPE = settings.get('USER_TYPE', ProviderType.BK.value)
# 转换为枚举类型
USER_TYPE = ProviderType(USER_TYPE)

# ---------------
# 云 API 相关配置
# ---------------

# 获取应用态的 AccessToken 的 API 地址
TOKEN_AUTH_ENDPOINT = settings.get('TOKEN_AUTH_ENDPOINT', f'{BK_SSM_URL}/api/v1/auth/access-tokens')
TOKEN_REFRESH_ENDPOINT = settings.get('TOKEN_REFRESH_ENDPOINT', f'{BK_SSM_URL}/api/v1/auth/access-tokens/refresh')
AUTH_ENV_NAME = settings.get('AUTH_ENV_NAME', 'prod')

# 请求 Token 服务所使用的默认 App Code 与 Secret
CLI_AUTH_CODE = settings.get('CLI_AUTH_CODE', '')
CLI_AUTH_SECRET = settings.get('CLI_AUTH_SECRET', '')


# === 插件应用相关
# 是否允许创建蓝鲸插件应用
IS_ALLOW_CREATE_BK_PLUGIN_APP = settings.get("IS_ALLOW_CREATE_BK_PLUGIN_APP", False)

# 是否开启插件开发功能
IS_ALLOW_PLUGIN_CENTER = settings.get("IS_ALLOW_PLUGIN_CENTER", False)

# [region-aware] 是否允许用户创建插件应用
BK_PLUGIN_CONFIG = settings.get('BK_PLUGIN_CONFIG', {'allow_creation': IS_ALLOW_CREATE_BK_PLUGIN_APP})

# 管理插件应用的 API 网关时所使用的配置：
BK_PLUGIN_APIGW_SERVICE_STAGE = settings.get('BK_PLUGIN_APIGW_SERVICE_STAGE', 'prod')  # 环境（stage）
BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE = settings.get('BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE', 'default')  # 用户类型


# -------------
# 引擎相关配置项
# -------------

# === 环境变量相关配置
#
# 系统环境变量使用的前缀
CONFIGVAR_SYSTEM_PREFIX = 'BKPAAS_'
# 环境变量保留字段列表
CONFIGVAR_PROTECTED_NAMES = (
    "SLUG_URL",
    "HOME",
    "S3CMD_CONF",
    "HOSTNAME",
)
# 环境变量保留前缀列表
CONFIGVAR_PROTECTED_PREFIXES = settings.get('CONFIGVAR_PROTECTED_PREFIXES', ["BKPAAS_", "KUBERNETES_"])

# 用于校验内部服务间请求的 JWT 配置，携带用以下任何一个 key 签名的 JWT 的请求会被认为有效
PAAS_SERVICE_JWT_CLIENTS = get_paas_service_jwt_clients(settings)

# 应用构件包所使用对象存储配置
# Bucket 名称：保存应用源码包、初始化代码
BLOBSTORE_BUCKET_APP_SOURCE = settings.get('BLOBSTORE_BUCKET_APP_SOURCE', 'bkpaas3-slug-packages')
# Bucket 名称：保存应用模板代码
BLOBSTORE_BUCKET_TEMPLATES = settings.get('BLOBSTORE_BUCKET_TEMPLATES', 'bkpaas3-apps-tmpls')
# Bucket 名称：存储源码包
BLOBSTORE_BUCKET_AP_PACKAGES = settings.get('BLOBSTORE_BUCKET_AP_PACKAGES', 'bkpaas3-source-packages')

# S-Mart 应用默认增强服务配置信息
SMART_APP_DEFAULT_SERVICES_CONFIG = settings.get('SMART_APP_DEFAULT_SERVICES_CONFIG', {"mysql": {}})


# 针对 slug 环境对敏感信息加密密钥
SLUG_ENCRYPT_SECRET_KEY = settings.get("SLUG_ENCRYPT_SECRET_KEY", BKKRILL_ENCRYPT_SECRET_KEY)


# 默认进程规格套餐名称
DEFAULT_PROC_SPEC_PLAN = 'Starter'
PREMIUM_PROC_SPEC_PLAN = "4C2G5R"
ULTIMATE_PROC_SPEC_PLAN = "4C4G5R"


# 应用副本数相关配置：

# 按照进程名称与环境，配置默认副本数
ENGINE_PROC_REPLICAS_BY_TYPE = {
    # （进程类型, 环境名称）： 副本数量
    ('web', 'stag'): 1,
    ('web', 'prod'): 2,
}

# 如果应用源码打包后超过该尺寸，打印警告信息
ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB = 300

# 可恢复下架操作的最长时限
ENGINE_OFFLINE_RESUMABLE_SECS = 60


# == 应用运行时相关配置
#
# 默认运行时镜像名称
DEFAULT_RUNTIME_IMAGES = settings.get('DEFAULT_RUNTIME_IMAGES', {DEFAULT_REGION_NAME: "blueking"})

# ------------
# 增强服务相关
# ------------

# 各本地增强服务 vendor 基础配置
SERVICES_VENDOR_CONFIGS: Dict[str, Dict] = settings.get('SERVICES_VENDOR_CONFIGS', {})

# 后端轮询任务：刷新远程增强服务信息 - 默认轮询间隔
REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES = 5

# 是否禁用定时任务调度器
DISABLE_PERIODICAL_JOBS = settings.get("DISABLE_PERIODICAL_JOBS", False)

# 默认远程服务配置
SERVICE_REMOTE_ENDPOINTS: List[Dict] = get_service_remote_endpoints(settings)

# Transform to basic data type instead of using BoxList directly to avoid not pickle-able bug
# See: paasng/paasng/dev_resources/servicehub/remote/store.py for more information
if hasattr(SERVICE_REMOTE_ENDPOINTS, 'to_list'):
    SERVICE_REMOTE_ENDPOINTS = SERVICE_REMOTE_ENDPOINTS.to_list()

# 无须用户关心的保留服务规格
SERVICE_PROTECTED_SPEC_NAMES = ["app_zone"]

# 集群名与 app_zone 的映射，app_zone 会在应用申请增强服务实例时用到
# 其默认值为 universal。如果你需要为集群配置特殊值，也可修改该配置项，
# 比如 APP_ZONE_CLUSTER_MAPPINGS = {"main-cluster": "another-zone"}
APP_ZONE_CLUSTER_MAPPINGS = settings.get('APP_ZONE_CLUSTER_MAPPINGS', {})

# 为不同应用类型所配置的预设增强服务，默认为任何类型都为空
# 示例格式：{'default': {'mysql': {'specs': {'version': '5.7'}}, 'redis': {}}, 'bk_plugin': ...}
PRESET_SERVICES_BY_APP_TYPE: Dict[str, Dict] = settings.get('PRESET_SERVICES_BY_APP_TYPE', {})

# ---------------
# 应用市场相关配置
# ---------------

BK_CONSOLE_DBCONF = get_database_conf(
    settings, encrypted_url_var='PAAS_LEGACY_DATABASE_URL', env_var_prefix='BK_CONSOLE_', for_tests=RUNNING_TESTS
)

# 是否需要填写应用联系人
APP_REQUIRE_CONTACTS = settings.get('APP_REQUIRE_CONTACTS', False)

# ------------------
# 应用监控服务相关配置
# ------------------

# 监控服务 phalanx 地址
PHALANX_URL = settings.get('PHALANX_URL', "http://localhost:8080")

# 监控服务 phalanx 访问 token
PHALANX_AUTH_TOKEN = settings.get('PHALANX_AUTH_TOKEN', '')


# --------------
# 平台日志相关配置
# --------------

# 是否将 PaaS API 请求日志发送给 Redis 队列
PAAS_API_LOG_REDIS_HANDLER = settings.get(
    'PAAS_API_LOG_REDIS_HANDLER',
    {
        # 开关，默认不发送
        'enabled': False,
        'url': 'redis://localhost:6379/0',
        'queue_name': 'paas_ng-meters',
        'tags': [],
    },
)


# --------------
# 应用日志相关配置
# --------------
# 默认的日志采集器类型, 可选性 "ELK", "BK_LOG"
# 低于 k8s 1.12 的集群不支持蓝鲸日志平台采集器, 如需要支持 k8s 1.12 版本(含) 以下集群, 默认值不能设置成 BK_LOG
LOG_COLLECTOR_TYPE = settings.get("LOG_COLLECTOR_TYPE", "ELK")

# 日志 ES 服务地址
ELASTICSEARCH_HOSTS = settings.get('ELASTICSEARCH_HOSTS', [{'host': 'localhost', 'port': "9200"}])

# 日志 ES 搜索超时时间
DEFAULT_ES_SEARCH_TIMEOUT = 30

# 日志 Index 名称模式
ES_K8S_LOG_INDEX_PATTERNS = settings.get('ES_K8S_LOG_INDEX_PATTERNS', 'app_log-*')
# 接入层日志 Index 名称模式
ES_K8S_LOG_INDEX_NGINX_PATTERNS = settings.get('ES_K8S_LOG_INDEX_NGINX_PATTERNS', "app_log-nginx-(?P<date>.+)")

# 不允许查询日志的关键词
ES_JSON_FIELD_BLACKLIST = ["json.message", "json.asctime", "json.process"]
# 日志高亮标签，用于前端高亮显示结果
BK_LOG_HIGHLIGHT_TAG = ("[bk-mark]", "[/bk-mark]")


# ---------------
# 访问控制相关配置
# ---------------

# [region-aware] 访问控制主配置
ACCESS_CONTROL_CONFIG = settings.get(
    'ACCESS_CONTROL_CONFIG',
    {
        "module": ["user_access_control"],
        "enabled_by_default": [],
        "disable_switch_off": [],
        "user_type": "qq",
        # 用户字段名称
        "user_tips": "username_field",
        "redis": {},
    },
)


# 白名单策略默认生效时长，单位为天
# NOTE: 根据业务层的反馈, 白名单申请时间过短会导致开发商需要频发申请权限. 反馈建议默认时间设置成 90d - 180d 比较合适. 因此这里取值 90d
ACCESS_CONTROL_STRATEGY_DEFAULT_EXPIRES_DAYS = 90

# ---------------
# 访问统计相关配置
# ---------------

PAAS_ANALYSIS_BASE_URL = settings.get('PAAS_ANALYSIS_BASE_URL', 'http://localhost:8085')
PAAS_ANALYSIS_JWT_CONF = settings.get('PAAS_ANALYSIS_JWT_CONF', {})


# ---------------
# 搜索服务相关配置
# ---------------

# 腾讯 iwiki 服务相关配置
IWIKI_WEB_UI_BASE_URL = settings.get('IWIKI_WEB_UI_BASE_URL', 'http://localhost:8080')
IWIKI_API_BASE_URL = settings.get('IWIKI_API_BASE_URL', 'http://localhost:8080')
IWIKI_API_RIO_GW_TOKEN = settings.get('IWIKI_API_RIO_GW_TOKEN', '')

# 腾讯码客相关配置
MK_SEARCH_API_BASE_URL = settings.get('MK_SEARCH_API_BASE_URL', 'http://localhost:8080')
MK_SEARCH_API_RIO_GW_TOKEN = settings.get('MK_SEARCH_API_RIO_GW_TOKEN', '')
MK_SEARCH_API_PRIVATE_TOKEN = settings.get('MK_SEARCH_API_PRIVATE_TOKEN', '')


# ---------------
# 应用一键迁移配置
# ---------------

# 是否开启应用迁移相关功能
ENABLE_MANAGE_LEGACY_APP = settings.get('ENABLE_MANAGE_LEGACY_APP', False)

# 一键迁移超时时间
LEGACY_APP_MIGRATION_PROCESS_TIMEOUT = 600

# 一键迁移部署超时时间
LEGACY_APP_MIGRATION_DEPLOY_TIMEOUT = 1200

# 迁移超期未完成提醒，天数，超过期限后每次正式部署都有弹框提醒
MIGRATION_REMIND_DAYS = 7

# 迁移时，是否 patch 用户代码
IS_PATCH_CODE_IN_MGRLEGACY = settings.get('IS_PATCH_CODE_IN_MGRLEGACY', True)

# ------------------
# 蓝盾代码检查相关配置
# ------------------

# 蓝鲸 CI 相关配置项
CI_CONFIGS = settings.get('CI_CONFIGS', {})

# ------------------
# 蓝鲸文档中心配置
# ------------------
# 蓝鲸PaaS3.0资料库地址
BKDOC_URL = settings.get('BKDOC_URL', 'http://localhost:8080')

# 文档应用的应用ID
BK_DOC_APP_ID = settings.get('BK_DOC_APP_ID', 'bk_docs_center')

# 蓝鲸官网文档中心地址，若镜像中没有设置该环境变量的值则设置为应用（BK_DOC_APP_ID）的访问地址
BK_DOCS_URL_PREFIX = settings.get('BK_DOCS_URL_PREFIX', 'https://bk.tencent.com/docs')

# 平台FAQ 地址
PLATFORM_FAQ_URL = settings.get('PLATFORM_FAQ_URL', f'{BK_DOCS_URL_PREFIX}/markdown/PaaS3.0/faq')

# 是否有人工客服
SUPPORT_LIVE_AGENT = settings.get('SUPPORT_LIVE_AGENT', False)
# 人工客服配置
LIVE_AGENT_CONFIG = settings.get('LIVE_AGENT_CONFIG', {'text': '联系客服', 'link': 'about:blank'})

# 是否开启终端色彩
COLORFUL_TERMINAL_OUTPUT = True

# ------------------
# S-Mart 应用镜像化配置
# ------------------

# S-Mart 镜像仓库的 Registry 的域名
SMART_DOCKER_REGISTRY_HOST = settings.get('SMART_DOCKER_REGISTRY_ADDR', 'registry.hub.docker.com')
# S-Mart 镜像仓库的命名空间, 即在 Registry 中的项目名
SMART_DOCKER_REGISTRY_NAMESPACE = settings.get('SMART_DOCKER_NAMESPACE', 'bkpaas/docker')
# 用于访问 Registry 的账号
SMART_DOCKER_REGISTRY_USERNAME = settings.get('SMART_DOCKER_USERNAME', 'bkpaas')
# 用于访问 Registry 的密码
SMART_DOCKER_REGISTRY_PASSWORD = settings.get('SMART_DOCKER_PASSWORD', 'blueking')
# S-Mart 基础镜像信息
SMART_IMAGE_NAME = f"{SMART_DOCKER_REGISTRY_NAMESPACE}/slug-pilot"
SMART_IMAGE_TAG = 'heroku-18-v1.6.1'


# ------------------
# App 应用镜像仓库配置
# ------------------
# App 镜像仓库的 Registry 的域名
APP_DOCKER_REGISTRY_HOST = settings.get('APP_DOCKER_REGISTRY_ADDR', 'registry.hub.docker.com')
# App 镜像仓库的命名空间, 即在 Registry 中的项目名
APP_DOCKER_REGISTRY_NAMESPACE = settings.get('APP_DOCKER_NAMESPACE', 'bkpaas/docker')
# 用于访问 Registry 的账号
APP_DOCKER_REGISTRY_USERNAME = settings.get('APP_DOCKER_USERNAME', 'bkpaas')
# 用于访问 Registry 的密码
APP_DOCKER_REGISTRY_PASSWORD = settings.get('APP_DOCKER_PASSWORD', 'blueking')


# ------------------
# bk-lesscode 相关配置
# ------------------
# bk_lesscode 注册在 APIGW 上的环境
BK_LESSCODE_APIGW_STAGE = settings.get('BK_LESSCODE_APIGW_STAGE', 'prod')
# bk_lesscode 平台访问地址
BK_LESSCODE_URL = settings.get('BK_LESSCODE_URL', '')
# bk_lesscode API 是否已经注册在 APIGW 网关上
ENABLE_BK_LESSCODE_APIGW = settings.get('ENABLE_BK_LESSCODE_APIGW', False)
BK_LESSCODE_TIPS = settings.get('BK_LESSCODE_TIPS', "")

# -----------------
# 源码托管相关配置项
# -----------------

DOCKER_REGISTRY_CONFIG = settings.get(
    'DOCKER_REGISTRY_CONFIG', {"DEFAULT_REGISTRY": "https://hub.docker.com", "ALLOW_THIRD_PARTY_REGISTRY": False}
)

# -----------------
# 插件开发中心配置项
# -----------------
# 插件中心「源码仓库」相关配置
PLUGIN_REPO_CONF = settings.get("PLUGIN_REPO_CONF")

# 插件开发中心在权限中心注册的系统 ID
IAM_PLUGINS_CENTER_SYSTEM_ID = settings.get('IAM_PLUGINS_CENTER_SYSTEM_ID', default='bk_plugins')

# 是否在开发者中心应用列表中展示插件应用
DISPLAY_BK_PLUGIN_APPS = settings.get("DISPLAY_BK_PLUGIN_APPS", True)

# -----------------
# 蓝鲸监控配置项
# -----------------
# 是否支持使用蓝鲸监控，启用后才能在社区版提供指标信息
ENABLE_BK_MONITOR = settings.get('ENABLE_BK_MONITOR', False)
# 蓝鲸监控运维相关的额外配置
BKMONITOR_METRIC_RELABELINGS = settings.get('BKMONITOR_METRIC_RELABELINGS', [])
# 蓝鲸监控的API是否已经注册在 APIGW
ENABLE_BK_MONITOR_APIGW = settings.get("ENABLE_BK_MONITOR_APIGW", True)
# 同步告警策略到监控的配置
MONITOR_AS_CODE_CONF = settings.get('MONITOR_AS_CODE_CONF', {})
# Rabbitmq 监控配置项, 格式如 {'enabled': True, 'metric_name_prefix': '', 'service_name': 'rabbitmq'}
RABBITMQ_MONITOR_CONF = settings.get('RABBITMQ_MONITOR_CONF', {})
# 蓝鲸监控网关的环境
BK_MONITOR_APIGW_SERVICE_STAGE = settings.get('BK_MONITOR_APIGW_SERVICE_STAGE', 'stage')

# ---------------------------------------------
# （internal）内部配置，仅开发项目与特殊环境下使用
# ---------------------------------------------

FOR_TESTS_LEGACY_APP_CODE = settings.get('FOR_TESTS_LEGACY_APP_CODE', 'test-app')
# 用于测试的真实可连接的 svn 服务器地址，如提供，将会在单元测试执行真实的 export 等操作
FOR_TESTS_SVN_SERVER_CONF = settings.get('FOR_TESTS_SVN_SERVER_CONF')
FOR_TESTS_APP_SVN_INFO = settings.get('FOR_TESTS_APP_SVN_INFO')

PAAS_X_BK_DATA_DB_CONF = settings.get('PAAS_X_BK_DATA_DB_CONF', {})
DEBUG_FORCE_DISABLE_CSRF = settings.get('DEBUG_FORCE_DISABLE_CSRF', False)

# Sentry 错误收集服务配置
SENTRY_CONFIG = settings.get('SENTRY_CONFIG', {})

# openTelemetry trace 配置，默认不启用
ENABLE_OTEL_TRACE = settings.get('ENABLE_OTEL_TRACE', False)
OTEL_INSTRUMENT_DB_API = settings.get('OTEL_INSTRUMENT_DB_API', True)
# 上报数据服务名称
OTEL_SERVICE_NAME = settings.get('OTEL_SERVICE_NAME', 'bkpaas3-apiserver')
# sdk 采样规则（always_on / always_off / parentbased_always_on...）
OTEL_SAMPLER = settings.get('OTEL_SAMPLER', 'always_on')
OTEL_BK_DATA_TOKEN = settings.get('OTEL_BK_DATA_TOKEN', '')
OTEL_GRPC_URL = settings.get('OTEL_GRPC_URL', '')

if ENABLE_OTEL_TRACE:
    INSTALLED_APPS += ('paasng.tracing',)

# 本选项默认关闭。表示注入到应用运行环境中的 {prefix}_SUB_PATH 环境变量总是使用真实值（基于算法的最短子路径）。
# 开启后将总是使用静态值：{region}-{engine-app-name} ，仅限特殊路由规则的部署环境启用。
FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE = settings.get('FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE', False)

# 是否启用格式为 `/{region}-{engine_app_name}/` 的子路径，仅供某些需向前兼容的特殊
# 环境下使用，默认关闭。
USE_LEGACY_SUB_PATH_PATTERN = settings.get('USE_LEGACY_SUB_PATH_PATTERN', False)

# 初始化的第三方应用(外链应用)的 code,多个以英文逗号分割
THIRD_APP_INIT_CODES = settings.get('THIRD_APP_INIT_CODES', '')

# 允许通过 API 创建第三方应用(外链应用)的系统ID,多个以英文逗号分割
ALLOW_THIRD_APP_SYS_IDS = settings.get('ALLOW_THIRD_APP_SYS_IDS', '')
ALLOW_THIRD_APP_SYS_ID_LIST = ALLOW_THIRD_APP_SYS_IDS.split(",") if ALLOW_THIRD_APP_SYS_IDS else []

# 引入 workloads 相关配置
# fmt: off
from . import workloads as workloads_settings

for key in dir(workloads_settings):
    if key in ["BASE_DIR", "SETTINGS_FILES_GLOB", "LOCAL_SETTINGS"] or not key.isupper():
        continue
    if key in locals() and getattr(workloads_settings, key) != locals()[key]:
        raise KeyError("Can't override apiserver settings, duplicated key: {}".format(key))
    locals()[key] = getattr(workloads_settings, key)
# fmt: on
