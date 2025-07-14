# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

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
import ssl
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymysql
import urllib3
from bkpaas_auth.core.constants import ProviderType
from django.contrib import messages
from django.db.backends.mysql.features import DatabaseFeatures
from django.utils.encoding import force_bytes, force_str
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from dynaconf import LazySettings, Validator
from environ import Env
from moby_distribution.registry.utils import parse_image

from .utils import (
    cache_redis_sentinel_url,
    get_database_conf,
    get_default_keepalive_options,
    get_paas_service_jwt_clients,
    get_service_remote_endpoints,
    is_in_celery_worker,
    is_redis_backend,
    is_redis_sentinel_backend,
)

BASE_DIR = Path(__file__).parents[2]

SETTINGS_FILES_GLOB = str(BASE_DIR / "settings_files/*.yaml")
LOCAL_SETTINGS = str(BASE_DIR / "settings_local.yaml")

settings = LazySettings(
    environments=False,
    load_dotenv=True,
    includes=[SETTINGS_FILES_GLOB, LOCAL_SETTINGS],
    validators=[
        # Configure minimal required settings
        Validator("BKKRILL_ENCRYPT_SECRET_KEY", must_exist=True),
    ],
    # Env var name configs
    ENVVAR_PREFIX_FOR_DYNACONF="PAAS",
    ENVVAR_FOR_DYNACONF="PAAS_SETTINGS",
)

_notset = object()

# Patch the SSL module for compatibility with legacy CA credentials.
# https://stackoverflow.com/questions/72479812/how-to-change-tweak-python-3-10-default-ssl-settings-for-requests-sslv3-alert
urllib3.util.ssl_.DEFAULT_CIPHERS = "ALL:@SECLEVEL=1"


class PatchFeatures:
    """Patched Django Features"""

    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:  # noqa
            return (10, 4)
        else:
            return (5, 7)


# Django 4.2+ 不再官方支持 Mysql 5.7，但目前 Django 仅是对 5.7 做了软性的不兼容改动，
# 在没有使用 8.0 特异的功能时，对 5.7 版本的使用无影响，为兼容存量的 Mysql 5.7 DB 做此 Patch
DatabaseFeatures.minimum_database_version = PatchFeatures.minimum_database_version  # noqa

pymysql.install_as_MySQLdb()

# 蓝鲸数据库内容加密私钥
# 使用 `from cryptography.fernet import Fernet; Fernet.generate_key()` 生成随机秘钥
# 详情查看：https://cryptography.io/en/latest/fernet/
BKKRILL_ENCRYPT_SECRET_KEY = force_bytes(settings.get("BKKRILL_ENCRYPT_SECRET_KEY", ""))

# Django 项目使用的 SECRET_KEY，如未配置，使用 BKKRILL 的 secret key 替代
SECRET_KEY = settings.get("SECRET_KEY") or force_str(BKKRILL_ENCRYPT_SECRET_KEY)

# 选择加密数据库内容的算法，可选择：'SHANGMI' , 'CLASSIC'
BK_CRYPTO_TYPE = settings.get("BK_CRYPTO_TYPE", "CLASSIC")
ENCRYPT_CIPHER_TYPE = "SM4CTR" if BK_CRYPTO_TYPE == "SHANGMI" else "FernetCipher"

DEBUG = settings.get("DEBUG", False)

SESSION_COOKIE_HTTPONLY = False

RUNNING_TESTS = "test" in sys.argv or "pytest" in sys.argv[0] or "PYTEST_XDIST_TESTRUNUID" in os.environ

INSTALLED_APPS = [
    # WARNING: never enable django.contrib.admin here
    # Enable auth and contenttypes but don't migrate tables
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_yasg",
    "bootstrap3",
    "corsheaders",
    "webpack_loader",
    "django_prometheus",
    "paasng.misc.plat_config",
    "paasng.infras.accounts",
    "paasng.infras.sysapi_client",
    "paasng.platform.applications",
    "paasng.accessories.log",
    "paasng.platform.modules",
    "paasng.infras.oauth2",
    "paasng.misc.operations",
    "paasng.platform.environments",
    "paasng.accessories.ci",
    "paasng.platform.bkapp_model",
    "paasng.platform.engine",
    "paasng.platform.engine.streaming",
    "paasng.platform.evaluation",
    "paasng.accessories.publish.market",
    "paasng.accessories.publish.sync_market",
    "paasng.platform.sourcectl",
    "paasng.accessories.servicehub",
    "paasng.accessories.services",
    # dev_sandbox
    "paasng.accessories.dev_sandbox",
    "paasng.platform.templates",
    "paasng.plat_admin.api_doc",
    "paasng.plat_admin.admin42",
    "paasng.plat_admin.system",
    "paasng.plat_admin.admin_cli",
    "paasng.misc.monitoring.monitor",
    "paasng.misc.monitoring.healthz",
    "paasng.misc.monitoring.metrics",
    "paasng.misc.search",
    "paasng.accessories.smart_advisor",
    "paasng.platform.bk_lesscode",
    "paasng.infras.iam.bkpaas_iam_migration",
    "paasng.infras.iam.members",
    "paasng.infras.bkmonitorv3",
    "paasng.platform.declarative",
    "paasng.platform.smart_app",
    "paasng.bk_plugins.bk_plugins",
    "paasng.bk_plugins.pluginscenter",
    "paasng.bk_plugins.pluginscenter.iam_adaptor",
    "paasng.platform.mgrlegacy",
    "bkpaas_auth",
    "apigw_manager.apigw",
    "paasng.plat_admin.initialization",
    # Put "scheduler" in the last position so models in other apps can be ready
    "paasng.platform.scheduler",
    "paasng.misc.audit",
    "revproxy",
    # workloads apps
    "paas_wl.bk_app.applications",
    "paas_wl.infras.cluster",
    "paas_wl.workloads.networking.egress",
    "paas_wl.workloads.networking.ingress",
    "paas_wl.workloads.networking.entrance",
    "paas_wl.infras.resource_templates",
    "paas_wl.workloads.release_controller.hooks",
    "paas_wl.bk_app.processes",
    "paas_wl.workloads.images",
    "paas_wl.bk_app.monitoring.app_monitor",
    "paas_wl.bk_app.cnative.specs",
    "paas_wl.bk_app.deploy",
    "paas_wl.infras.resources.generation",
    # 蓝鲸通知中心
    "bk_notice_sdk",
]

# Allow extending installed apps
EXTRA_INSTALLED_APPS = settings.get("EXTRA_INSTALLED_APPS", [])
INSTALLED_APPS += EXTRA_INSTALLED_APPS

# The "perm_insure" module helps us to make sure that the permission is configured
# correctly, put it at the end of the list to make sure that all URL confs have been
# added to the root url before the perm checking starts.
INSTALLED_APPS.append("paasng.infras.perm_insure")

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "paasng.infras.accounts.middlewares.RequestIDProvider",  # 注入 RequestID
    "paasng.utils.api_middleware.ApiLogMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "paasng.utils.middlewares.WhiteNoiseRespectPrefixMiddleware",
    "bkpaas_auth.middlewares.CookieLoginMiddleware",
    "paasng.infras.accounts.middlewares.SiteAccessControlMiddleware",
    "paasng.infras.sysapi_client.middlewares.PrivateTokenAuthenticationMiddleware",
    # API Gateway related
    "apigw_manager.apigw.authentication.ApiGatewayJWTGenericMiddleware",  # JWT 认证
    "apigw_manager.apigw.authentication.ApiGatewayJWTAppMiddleware",  # JWT 透传的应用信息
    # TODO 在 JWT 透传应用信息的基础上, header 带 bk_username. 非推荐做法, 后续考虑移除
    # Must placed below `ApiGatewayJWTAppMiddleware` because it depends on `request.app`
    "paasng.infras.accounts.middlewares.WrapUsernameAsUserMiddleware",
    "apigw_manager.apigw.authentication.ApiGatewayJWTUserMiddleware",  # JWT 透传的用户信息
    # Must placed below `ApiGatewayJWTAppMiddleware` because it depends on `request.app`
    "paasng.infras.sysapi_client.middlewares.AuthenticatedAppAsClientMiddleware",
    # Other utilities middlewares
    "paasng.utils.middlewares.AutoDisableCSRFMiddleware",
    "paasng.utils.middlewares.APILanguageMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# 管理者用户：拥有全量应用权限（经权限中心鉴权）
ADMIN_USERNAME = settings.get("ADMIN_USERNAME", "admin")

AUTH_USER_MODEL = "bkpaas_auth.User"

AUTHENTICATION_BACKENDS = ["bkpaas_auth.backends.UniversalAuthBackend", "bkpaas_auth.backends.APIGatewayAuthBackend"]

# FIXME: Enable this will cause 500 Error, will fix later
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = "paasng.urls"

# 从 request.META 读取 request_id 的键
REQUEST_ID_META_KEY = "HTTP_X_REQUEST_ID"
# 发起请求时，将 request_id 设置在 headers 中的键
REQUEST_ID_HEADER_KEY = "X-Request-Id"

WSGI_APPLICATION = "paasng.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "zh-cn"
LANGUAGES = (
    ("zh-cn", "简体中文"),
    ("en", "English"),
)
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 国际化 cookie 信息必须跟整个蓝鲸体系保存一致
LANGUAGE_COOKIE_NAME = "blueking_language"
LANGUAGE_COOKIE_PATH = "/"
# 国际化 cookie 默认写在整个蓝鲸的根域下
LANGUAGE_COOKIE_DOMAIN = settings.get("BK_COOKIE_DOMAIN")

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

CHANGELOG_PATH = os.path.join(BASE_DIR, "changelog")

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
SITE_URL = "/"
STATIC_ROOT = str(BASE_DIR / "public" / "static")

STATIC_URL = settings.get("STATIC_URL", "/static/")

STATICFILES_DIRS = (
    # Staticfile path generated by webpack
    str(BASE_DIR / "public" / "assets"),
)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

WEBPACK_LOADER = {
    "DEFAULT": {
        "BUNDLE_DIR_NAME": "bundles/",
        "STATS_FILE": str(BASE_DIR / "public" / "webpack-stats.json"),
    }
}

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

TEMPLATE_CONTEXT_PROCESSORS = (
    # the context to the templates
    "django.contrib.auth.context_processors.auth",
    "django.template.context_processors.request",
    "django.template.context_processors.csrf",
    "django.template.context_processors.i18n",
    "paasng.plat_admin.admin42.context_processors.admin_config",
)

TEMPLATE_DIRS = [str(BASE_DIR / "templates")]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": list(TEMPLATE_DIRS),
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": list(TEMPLATE_CONTEXT_PROCESSORS),
        },
    },
]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "paasng.utils.views.custom_exception_handler",
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.SessionAuthentication",),
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    # TIPS: 覆盖 SearchFilter、OrderingFilter 的过滤参数，与应用列表保持用同样的搜索、排序字段
    "SEARCH_PARAM": "search_term",
    "ORDERING_PARAM": "order_by",
    # 增加为蓝鲸 API 规范设计的 Renderer
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        # 可将 Response 转换为蓝鲸 API 规范所规定的格式： {"result": true, "message": "error", ...}
        "paasng.utils.views.BkStandardApiJSONRenderer",
    ],
}

# 自定义 drf-yasg 配置
SWAGGER_SETTINGS = {
    "DEFAULT_AUTO_SCHEMA_CLASS": "paasng.plat_admin.api_doc.extended_auto_schema.ExtendedSwaggerAutoSchema",
    "DEFAULT_GENERATOR_CLASS": "paasng.plat_admin.api_doc.generators.OpenAPISchemaGenerator",
}

MESSAGE_TAGS = {messages.ERROR: "danger"}

LOG_LEVEL = settings.get("LOG_LEVEL", default="INFO")

# Get the logging directory config, if configured the logs will be written to local directory
# in the configured format(json/text).
#
# 存放日志文件的目录，默认不打印任何日志文件
LOGGING_DIRECTORY = settings.get("LOGGING_DIRECTORY", default=None)
# 日志文件格式，可选值为：json/text
LOGGING_FILE_FORMAT = settings.get("LOGGING_FILE_FORMAT", default="json")

if LOGGING_DIRECTORY is None:
    logging_to_console = True
    logging_directory = None
else:
    logging_to_console = False
    # The dir allows both absolute and relative path, when it's relative, combine
    # the value with project's base directory
    logging_directory = Path(BASE_DIR) / Path(LOGGING_DIRECTORY)
    logging_directory.mkdir(exist_ok=True)

# 是否总是打印日志到控制台，默认关闭
LOGGING_ALWAYS_CONSOLE = settings.get("LOGGING_ALWAYS_CONSOLE", default=False)
if LOGGING_ALWAYS_CONSOLE:
    logging_to_console = True


def build_logging_config(log_level: str, to_console: bool, file_directory: Optional[Path], file_format: str) -> Dict:
    """Build the global logging config dict.

    :param log_level: The log level.
    :param to_console: If True, output the logs to the console.
    :param file_directory: If the value is not None, output the logs to the given directory.
    :param file_format: The format of the logging file, "json" or "text".
    :return: The logging config dict.
    """

    def _build_file_handler(log_path: Path, filename: str, format: str) -> Dict:
        formatter = "verbose_json" if format == "json" else "verbose"
        return {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "level": log_level,
            "formatter": formatter,
            "filename": str(log_path / filename),
            # Set max file size to 100MB
            "maxBytes": 100 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_id"],
        }

    handlers = []
    handlers_config: Dict[str, Any] = {
        "null": {"level": log_level, "class": "logging.NullHandler"},
        "mail_admins": {"level": log_level, "class": "django.utils.log.AdminEmailHandler"},
        "console": {
            "level": log_level,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
    }
    if to_console:
        handlers.append("console")

    if file_directory:
        if file_format in ("json", "text"):
            base_filename = "main-celery" if is_in_celery_worker() else "main"
            filename = f"{base_filename}-{file_format}.log"
            handlers.append("file")
            handlers_config["file"] = _build_file_handler(file_directory, filename, file_format)
        else:
            raise ValueError(f"Invalid file_format: {file_format}")

    logging_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "%(levelname)s [%(asctime)s] [%(request_id)s] %(name)s(ln:%(lineno)d): %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "verbose_json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": (
                    "%(levelname)s %(asctime)s %(pathname)s %(lineno)d %(funcName)s %(process)d %(thread)d %(message)s"
                ),
            },
            "simple": {"format": "%(levelname)s %(message)s"},
        },
        "filters": {
            "request_id": {"()": "paasng.utils.logging.RequestIDFilter"},
        },
        "handlers": handlers_config,
        "root": {"handlers": handlers, "level": log_level, "propagate": False},
        "loggers": {
            "django": {"handlers": ["null"], "level": log_level, "propagate": False},
            "django.request": {"handlers": handlers, "level": "ERROR", "propagate": False},
            "django.security": {"level": "INFO"},
            # 常用模块日志级别
            "paasng": {"level": "NOTSET"},
            "commands": {"handlers": handlers, "level": log_level, "propagate": False},
            # 设置第三方模块日志级别，避免日志过多
            "bkpaas_auth": {"level": "WARNING"},
            "apscheduler": {"level": "WARNING"},
            "requests": {"level": "ERROR"},
            "urllib3.connectionpool": {"level": "ERROR", "handlers": ["console"], "propagate": False},
            "boto3": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "botocore": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "console": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "iam": {
                "level": settings.get("IAM_LOG_LEVEL", "ERROR"),
                "handlers": handlers,
                "propagate": False,
            },
        },
    }
    if settings.get("LOGGING_ENABLE_SQL_QUERIES", False):
        logging_dict["loggers"]["django.db.backends"] = {  # type: ignore
            "handlers": handlers,
            "level": log_level,
            "propagate": True,
        }
    return logging_dict


LOGGING = build_logging_config(LOG_LEVEL, logging_to_console, logging_directory, LOGGING_FILE_FORMAT)

# 发送通知的渠道，如果没有配置，则仅记录日志并不调用发送通知的 API
BK_CMSI_ENABLED_METHODS = settings.get("BK_CMSI_ENABLED_METHODS", ["send_mail", "send_sms", "send_weixin"])

# ------------------------
# Django 基础配置（自定义）
# ------------------------

DATABASES = {}

# When running "collectstatic" command, the database config is not available, so we
# make it optional.
if default_db_conf := get_database_conf(settings):
    DATABASES["default"] = default_db_conf
if wl_db_conf := get_database_conf(settings, encrypted_url_var="WL_DATABASE_URL", env_var_prefix="WL_"):
    DATABASES["workloads"] = wl_db_conf

DATABASE_ROUTERS = ["paasng.core.core.storages.dbrouter.WorkloadsDBRouter"]

# == Redis 相关配置项，该 Redis 服务将被用于：缓存

# Redis 服务地址
REDIS_URL = settings.get("REDIS_URL", "redis://127.0.0.1:6379/0")
# Redis sentinel 模式配置
SENTINEL_MASTER_NAME = settings.get("SENTINEL_MASTER_NAME", "mymaster")
SENTINEL_PASSWORD = settings.get("SENTINEL_PASSWORD", "")

# 修改 Redis 连接时的 keepalive 配置，让连接更健壮
REDIS_CONNECTION_OPTIONS = {
    "socket_timeout": 3,
    "socket_connect_timeout": 3,
    "socket_keepalive": True,
    "socket_keepalive_options": get_default_keepalive_options(),
}

# == 缓存相关配置项
# DEFAULT_CACHE_CONFIG 优先级最高，若无该配置则检查是否配置 Redis，若存在则作为缓存, 否则使用临时文件作为缓存(仅适用于本地开发)
# WARNING: 生产环境请配置远程服务缓存, 如 RedisCache, DatabaseCache 等, 以保证多副本多 worker 时, 缓存数据一致, 否则可能无法正常工作
DEFAULT_CACHE_CONFIG = settings.get("DEFAULT_CACHE_CONFIG")
if DEFAULT_CACHE_CONFIG:
    CACHES = {"default": DEFAULT_CACHE_CONFIG}
elif REDIS_URL:
    CACHES = {
        "default": (
            cache_redis_sentinel_url(REDIS_URL, SENTINEL_MASTER_NAME, SENTINEL_PASSWORD)
            if is_redis_sentinel_backend(REDIS_URL)
            else Env.cache_url_config(REDIS_URL)
        )
    }
else:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.filebased.FileBasedCache", "LOCATION": "/tmp/django_cache"}
    }

# 修改默认 Cookie 名称，避免冲突
SESSION_COOKIE_NAME = "bk_paas3_sessionid"
CSRF_COOKIE_NAME = "bk_paas3_csrftoken"

FORCE_SCRIPT_NAME = settings.get("FORCE_SCRIPT_NAME")
CSRF_COOKIE_DOMAIN = settings.get("CSRF_COOKIE_DOMAIN")
SESSION_COOKIE_DOMAIN = settings.get("SESSION_COOKIE_DOMAIN")
# Django 4.0 会参考 Origin Header，如果使用了 CSRF_COOKIE_NAME，就需要在 settings 中额外配置 CSRF_TRUSTED_ORIGINS
# 且必须配置协议和域名
# https://docs.djangoproject.com/en/dev/releases/4.0/#format-change
BK_COOKIE_DOMAIN = settings.get("BK_COOKIE_DOMAIN")
# 正式环境 CSRF_COOKIE_DOMAIN 并未设置，所以默认值直接用通配符
CSRF_TRUSTED_ORIGINS = settings.get(
    "CSRF_TRUSTED_ORIGINS", [f"http://*{BK_COOKIE_DOMAIN}", f"https://*{BK_COOKIE_DOMAIN}"]
)

# 蓝鲸登录票据在 Cookie 中的名称，权限中心 API 未接入 APIGW，访问时需要提供登录态信息
BK_COOKIE_NAME = settings.get("BK_COOKIE_NAME", "bk_token")

# 允许通过什么域名访问服务，详见：https://docs.djangoproject.com/zh-hans/3.2/ref/settings/#allowed-hosts
ALLOWED_HOSTS = settings.get("ALLOWED_HOSTS", ["*"])

# CORS 请求跨域相关配置

# CORS 允许的来源
CORS_ORIGIN_REGEX_WHITELIST = settings.get("CORS_ORIGIN_REGEX_WHITELIST", [])

CORS_ORIGIN_ALLOW_ALL = settings.get("CORS_ORIGIN_ALLOW_ALL", False)

# 默认允许通过通过跨域请求传递 Cookie，默认允许
CORS_ALLOW_CREDENTIALS = True

# 跨域请求弹窗策略
# https://docs.djangoproject.com/en/4.2/topics/security/#cross-origin-opener-policy
SECURE_CROSS_ORIGIN_OPENER_POLICY = "unsafe-none"

# ============================ Celery 相关配置 ============================

CELERY_BROKER_URL = settings.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = settings.get("CELERY_RESULT_BACKEND", REDIS_URL)

if settings.get("CELERY_BROKER_HEARTBEAT", _notset) != _notset:
    CELERY_BROKER_HEARTBEAT = settings.get("CELERY_BROKER_HEARTBEAT")

# Celery 格式 / 时区相关配置
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ENABLE_UTC = False

CELERY_BROKER_TRANSPORT_OPTIONS = settings.get("CELERY_BROKER_TRANSPORT_OPTIONS", {})

if not CELERY_BROKER_TRANSPORT_OPTIONS and is_redis_backend(CELERY_BROKER_URL):
    # Set redis connection timeout and keep-alive to lower values
    CELERY_BROKER_TRANSPORT_OPTIONS = copy.deepcopy(REDIS_CONNECTION_OPTIONS)
    if is_redis_sentinel_backend(CELERY_BROKER_URL):
        # 添加 sentinel 配置
        CELERY_BROKER_TRANSPORT_OPTIONS.update(
            {
                "master_name": settings.get("CELERY_BROKER_SENTINEL_MASTER_NAME", SENTINEL_MASTER_NAME),
                "sentinel_kwargs": {"password": settings.get("CELERY_BROKER_SENTINEL_PASSWORD", SENTINEL_PASSWORD)},
            }
        )

if is_redis_sentinel_backend(CELERY_RESULT_BACKEND):
    # 添加 sentinel 配置
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
        "master_name": settings.get("CELERY_RESULT_BACKEND_SENTINEL_MASTER_NAME", SENTINEL_MASTER_NAME),
        "sentinel_kwargs": {"password": settings.get("CELERY_RESULT_BACKEND_SENTINEL_PASSWORD", SENTINEL_PASSWORD)},
    }

# Celery TLS 证书配置
CELERY_BROKER_USE_SSL = settings.get("CELERY_BROKER_USE_SSL") or None

if CELERY_BROKER_USE_SSL and isinstance(CELERY_BROKER_USE_SSL, dict):
    for k, v in CELERY_BROKER_USE_SSL.items():
        # 环境变量中只会将其设置为 bool 值，这里需要手动转换成 ssl 的枚举类值
        # 兼容 amqp -> cert_reqs, redis -> ssl_cert_reqs 两种 key
        # ref: https://docs.celeryq.dev/en/stable/userguide/configuration.html#broker-use-ssl
        if k in ["cert_reqs", "ssl_cert_reqs"]:
            # 只有显式指定为 False，才允许跳过证书检查
            CELERY_BROKER_USE_SSL[k] = ssl.CERT_NONE if v is False else ssl.CERT_REQUIRED

# Celery 队列名称
CELERY_TASK_DEFAULT_QUEUE = os.environ.get("CELERY_TASK_DEFAULT_QUEUE", "celery")

# 用于生成唯一且有意义的 ID 的函数导入路径，默认复用增强服务模块下的工具函数，一般情况下无需调整
UNIQUE_ID_GEN_FUNC = "paasng.accessories.services.utils.gen_unique_id"

# --------
# 系统配置
# --------

# 调用蓝鲸 API 的鉴权信息（BK_APP_CODE 用固定值）
BK_APP_CODE = settings.get("BK_APP_CODE", "bk_paas3")
BK_APP_SECRET = settings.get("BK_APP_SECRET", "")

# 是否启用多租户模式，本配置项仅支持在初次部署时配置，部署后不支持动态调整
ENABLE_MULTI_TENANT_MODE = settings.get("ENABLE_MULTI_TENANT_MODE", False)

# PaaS 2.0 在权限中心注册的系统ID （并非是平台的 Code）
IAM_SYSTEM_ID = settings.get("IAM_SYSTEM_ID", default="bk_paas")

# PaaS 3.0 在权限中心注册的系统 ID
IAM_PAAS_V3_SYSTEM_ID = settings.get("IAM_PAAS_V3_SYSTEM_ID", default="bk_paas3")

# 请求权限中心的鉴权信息
IAM_APP_CODE = settings.get("IAM_APP_CODE", default=BK_APP_CODE)
IAM_APP_SECRET = settings.get("IAM_APP_SECRET", default=BK_APP_SECRET)

# 额外指定的用于存储 migration 文件的 APP
# https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md#21-django-migration
BK_IAM_MIGRATION_APP_NAME = "bkpaas_iam_migration"

# 跳过初始化已有应用数据到权限中心（注意：仅跳过初始化数据，所有权限相关的操作还是依赖权限中心）
BK_IAM_SKIP = settings.get("BK_IAM_SKIP", False)

# IAM 权限生效时间（单位：秒）
# 权限中心的用户组授权是异步行为，即创建用户组，添加用户，对组授权后需要等待一段时间（10-20秒左右）才能鉴权
# 因此需要在应用创建后的一定的时间内，对创建者（拥有应用最高权限）的操作进行权限豁免以保证功能可正常使用
# 退出用户组同理，因此在退出的一定时间内，需要先 exclude 掉避免退出后还可以看到应用的问题
IAM_PERM_EFFECTIVE_TIMEDELTA = settings.get("BK_IAM_PERM_EFFECTIVE_TIMEDELTA", 5 * 60)


# 蓝鲸的云 API 地址，用于内置环境变量的配置项
BK_COMPONENT_API_URL = settings.get("BK_COMPONENT_API_URL", "")
# 蓝鲸的组件 API 地址，网关 SDK 依赖该配置项（该项值与 BK_COMPONENT_API_URL 一致）
COMPONENT_SYSTEM_HOST = settings.get("COMPONENT_SYSTEM_HOST", BK_COMPONENT_API_URL)
# 蓝鲸的组件 API 测试环境地址
COMPONENT_SYSTEM_HOST_IN_TEST = settings.get("COMPONENT_SYSTEM_HOST_IN_TEST", "http://localhost:8080")

BK_APIGW_NAME = settings.get("BK_APIGW_NAME")
# 网关运行环境
# TODO BK_LESSCODE_APIGW_STAGE 和 BK_IAM_APIGW_SERVICE_STAGE 考虑复用 APIGW_ENVIRONMENT?
APIGW_ENVIRONMENT = settings.get("APIGW_ENVIRONMENT", "prod")
# 网关 API 访问地址模板
BK_API_URL_TMPL = settings.get("BK_API_URL_TMPL", "http://localhost:8080/api/{api_name}/")
# 网关 API 默认网关环境
BK_API_DEFAULT_STAGE_MAPPINGS = settings.get("BK_API_DEFAULT_STAGE_MAPPINGS", {})

# 开发者中心 region 与 APIGW user_auth_type 的对应关系
REGION_TO_USER_AUTH_TYPE_MAP = settings.get("REGION_TO_USER_AUTH_TYPE_MAP", {"default": "default"})

# 提供 metrics 接口用的 client token 列表
METRIC_CLIENT_TOKEN_DICT = settings.get("METRIC_CLIENT_TOKEN_DICT", {})

# 是否默认允许创建 Smart 应用
IS_ALLOW_CREATE_SMART_APP_BY_DEFAULT = settings.get("IS_ALLOW_CREATE_SMART_APP_BY_DEFAULT", True)

# 使用“应用迁移”功能，迁移到云原生应用时所使用的目标集群名称
MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER = settings.get("MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER", "")

# 开发者中心使用的 k8s 集群组件（helm chart 名称）
BKPAAS_K8S_CLUSTER_COMPONENTS = settings.get(
    "BKPAAS_K8S_CLUSTER_COMPONENTS",
    [
        "bk-ingress-nginx",
        "bkapp-log-collection",
        "bkpaas-app-operator",
        "bcs-general-pod-autoscaler",
    ],
)

# 开发者安装的集群组件 Helm 仓库名（默认为 BCS 的公共仓库 -> public-repo）
CLUSTER_COMPONENT_HELM_REPO = settings.get("CLUSTER_COMPONENT_HELM_REPO", "public-repo")

# ---------------
# HealthZ 配置
# ---------------

# healthz: 将使用该 token 校验调用方身份，必须设置为有效字符串后方能生效
HEALTHZ_TOKEN = settings.get("HEALTHZ_TOKEN")

# 已启用探针列表
# 参照 paasng.misc.monitoring.healthz.probes 中包含的探针配置
HEALTHZ_PROBES = settings.get(
    "HEALTHZ_PROBES",
    [
        "paasng.misc.monitoring.healthz.probes.PlatformMysqlProbe",
        "paasng.misc.monitoring.healthz.probes.WorkloadsMysqlProbe",
        "paasng.misc.monitoring.healthz.probes.PlatformRedisProbe",
        "paasng.misc.monitoring.healthz.probes.ServiceHubProbe",
        "paasng.misc.monitoring.healthz.probes.PlatformBlobStoreProbe",
        "paasng.misc.monitoring.healthz.probes.BKIAMProbe",
    ],
)

# 蓝鲸的组件 API 的 Healthz 地址
COMPONENT_SYSTEM_HEALTHZ_URL = settings.get("COMPONENT_SYSTEM_HEALTHZ_URL", "http://localhost:8080")
# API 网关的 Healthz 地址
APIGW_HEALTHZ_URL = settings.get("APIGW_HEALTHZ_URL", "http://localhost:8080")

# ---------------
# 平台基础功能配置
# ---------------

# 是否自动创建用户，默认打开，关闭后新用户将无法访问
AUTO_CREATE_REGULAR_USER = settings.get("AUTO_CREATE_REGULAR_USER", True)

# 每个应用下最多创建的模块数量
MAX_MODULES_COUNT_PER_APPLICATION = settings.get("MAX_MODULES_COUNT_PER_APPLICATION", default=10, cast="@int")
# 应用单个模块允许创建的最大 process 数量
MAX_PROCESSES_PER_MODULE = settings.get("MAX_PROCESSES_PER_MODULE", default=16, cast="@int")

PAAS_LEGACY_DBCONF = get_database_conf(
    settings, encrypted_url_var="PAAS_LEGACY_DATABASE_URL", env_var_prefix="PAAS_LEGACY_", for_tests=RUNNING_TESTS
)

# 旧版本 PaaS 数据库，敏感字段所使用的加密 key
PAAS_LEGACY_DB_ENCRYPT_KEY = settings.get("PAAS_LEGACY_DB_ENCRYPT_KEY")

# ---------------
# 对象存储配置
# ---------------

BLOBSTORE_TYPE = settings.get("BLOBSTORE_TYPE")

# 应用构件包所使用对象存储配置
BLOBSTORE_S3_ENDPOINT = settings.get("BLOBSTORE_S3_ENDPOINT", default="http://127.0.0.1:9100")
BLOBSTORE_S3_ACCESS_KEY = settings.get("BLOBSTORE_S3_ACCESS_KEY", default="minio")
BLOBSTORE_S3_SECRET_KEY = settings.get("BLOBSTORE_S3_SECRET_KEY", default="")

# 对象存储 SDK 额外配置项，使用 minio 服务必须启用该配置
BLOBSTORE_S3_REGION_NAME = settings.get("BLOBSTORE_S3_REGION_NAME", "us-east-1")
BLOBSTORE_S3_SIG_VERSION = settings.get("BLOBSTORE_S3_SIG_VERSION", "s3v4")

# 用于存储 Logo 图片，默认与 BlobStore 使用相同配置
RGW_ENDPOINT_URL = settings.get("RGW_ENDPOINT_URL", default=BLOBSTORE_S3_ENDPOINT)
RGW_ACCESS_KEY_ID = settings.get("RGW_ACCESS_KEY_ID", default=BLOBSTORE_S3_ACCESS_KEY)
RGW_SECRET_ACCESS_KEY = settings.get("RGW_SECRET_ACCESS_KEY", default=BLOBSTORE_S3_SECRET_KEY)
RGW_STORAGE_BUCKET_NAME = "app-logo"

# 当配置该项时，使用 BK-Repo 而不是 S3 作为 BlobStore 存储
BLOBSTORE_BKREPO_CONFIG = settings.get("BLOBSTORE_BKREPO_CONFIG")
# bkrepo 项目名称，仅在创建项目时使用。bkrepo 的项目 ID 在 BLOBSTORE_BKREPO_CONFIG["PROJECT"] 中定义
# NOTE: 按目前 bkrepo 的规则，启用/关闭多租户模式的情况下:
# 关闭多租户: 项目 ID == 项目名称
# 启用多租户: 项目 ID == f"{租户 ID}_{项目名称}"
BLOBSTORE_BKREPO_PROJECT_NAME = settings.get("BLOBSTORE_BKREPO_PROJECT_NAME", "bkpaas")

# 增强服务 LOGO bucket
SERVICE_LOGO_BUCKET = settings.get("SERVICE_LOGO_BUCKET", "bkpaas3-platform-assets")
# 应用 Logo 存储 bucket 名称
APP_LOGO_BUCKET = settings.get("APP_LOGO_BUCKET", "bkpaas3-apps-logo")
# 应用 Logo 缓存时间设置
APP_LOGO_MAX_AGE = str(30 * 24 * 3600)
# 插件 Logo 存储 bucket 名称
PLUGIN_LOGO_BUCKET = settings.get("PLUGIN_LOGO_BUCKET", "bkpaas3-plugin-logo")
# 插件 Logo 缓存时间设置
PLUGIN_LOGO_MAX_AGE = str(30 * 24 * 3600)

# 蓝鲸PaaS平台访问地址，用于平台访问链接拼接与内置环境变量的配置项
BKPAAS_URL = settings.get("BKPAAS_URL", "")

# 蓝鲸 PaaS2.0 平台访问地址，用于平台访问链接拼接与内置环境变量的配置项
BK_PAAS2_URL = settings.get("BK_PAAS2_URL", "")

# 蓝鲸 PaaS2.0 平台内网访问地址，用于内置环境变量的配置项
BK_PAAS2_INNER_URL = settings.get("BK_PAAS2_INNER_URL", BK_PAAS2_URL)

# 应用默认 Logo 图片地址
APPLICATION_DEFAULT_LOGO = settings.get("APPLICATION_DEFAULT_LOGO", f"{BKPAAS_URL}/static/images/default_logo.png")

# 插件应用默认 Logo 图片地址
PLUGIN_APP_DEFAULT_LOGO = settings.get("PLUGIN_APP_DEFAULT_LOGO", APPLICATION_DEFAULT_LOGO)

# 蓝鲸 SSM 平台访问地址, 用于 access_token 验证
BK_SSM_URL = settings.get("BK_SSM_URL", "")

# deprecated：权限中心内网访问地址，用于对接权限中心.
# bk-iam sdk version >= 2.0.2 时, BK_IAM_V3_INNER_URL 已废弃
BK_IAM_V3_INNER_URL = settings.get("BK_IAM_V3_INNER_URL", "http://localhost:8080")

# 访问的权限中心 APIGW 版本
BK_IAM_APIGW_SERVICE_STAGE = settings.get("BK_IAM_APIGW_SERVICE_STAGE", "stage")

# 参数说明 https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md#22-config
# bk-iam sdk version >= 2.0.2 时, 只能通过 apigateway 访问 iam
BK_IAM_USE_APIGATEWAY = True

BK_IAM_APIGATEWAY_URL = settings.get(
    "BK_IAM_APIGATEWAY_URL", f"{BK_API_URL_TMPL.format(api_name='bk-iam')}/{BK_IAM_APIGW_SERVICE_STAGE}"
)

# 权限中心回调地址（provider api）
# 会存在开发者中心访问地址是 https 协议，但是 API 只能用 http 协议的情况，所以不能直接用 BKPAAS_URL
# ITSM 回调地址也复用了这个变量，修改变量名会涉及到 helm values 等多个地方同时修改，暂时先保留这个变量名
BK_IAM_RESOURCE_API_HOST = settings.get("BK_IAM_RESOURCE_API_HOST", BKPAAS_URL)

# 权限中心应用ID，用于拼接权限中心的在桌面的访问地址
BK_IAM_V3_APP_CODE = "bk_iam"

# 蓝鲸根域名
BK_DOMAIN = settings.get("BK_DOMAIN", "")
# 蓝鲸平台体系的地址，用于内置环境变量的配置项
BK_CC_URL = settings.get("BK_CC_URL", "")
BK_JOB_URL = settings.get("BK_JOB_URL", "")
BK_IAM_URL = settings.get("BK_IAM_URL", "")
BK_USER_URL = settings.get("BK_USER_URL", "")
BK_MONITORV3_URL = settings.get("BK_MONITORV3_URL", "")
BK_LOG_URL = settings.get("BK_LOG_URL", "")
BK_REPO_URL = settings.get("BK_REPO_URL", "")
BK_CI_URL = settings.get("BK_CI_URL", "")
BK_CODECC_URL = settings.get("BK_CODECC_URL", "")
BK_TURBO_URL = settings.get("BK_TURBO_URL", "")
BK_PIPELINE_URL = settings.get("BK_PIPELINE_URL", "")
BK_NODEMAN_URL = settings.get("BK_NODEMAN_URL", "")
BK_BCS_URL = settings.get("BK_BCS_URL", "")
BK_BSCP_URL = settings.get("BK_BSCP_URL", "")
BK_AUDIT_URL = settings.get("BK_AUDIT_URL", "")
# 蓝鲸产品 title/footer/name/logo 等资源自定义配置的路径
BK_SHARED_RES_URL = settings.get("BK_SHARED_RES_URL", "")

# 兼容 PaaS 2.0 注入的内置环境变量，确保应用迁移到 PaaS 3.0 后内置系统环境变量仍然有效
BK_PAAS2_PLATFORM_ENVS = settings.get(
    "BK_PAAS2_PLATFORM_ENVS",
    {
        "BK_IAM_INNER_HOST": {
            "value": settings.get("BK_IAM_INNER_URL", "http://:"),
            "description": _("蓝鲸权限中心旧版地址，建议切换为 BKPAAS_IAM_URL"),
        },
        "BK_IAM_V3_APP_CODE": {
            "value": settings.get("BK_IAM_V3_APP_CODE", "bk_iam"),
            "description": _("蓝鲸权限中心的应用ID"),
        },
        "BK_IAM_V3_INNER_HOST": {
            "value": BK_IAM_V3_INNER_URL,
            "description": _("蓝鲸权限中心内网访问地址，建议切换为 BKPAAS_IAM_URL"),
        },
        "BK_CC_HOST": {"value": BK_CC_URL, "description": _("蓝鲸配置平台访问地址，建议切换为 BKPAAS_CC_URL")},
        "BK_JOB_HOST": {"value": BK_JOB_URL, "description": _("蓝鲸作业平台访问地址，建议切换为 BKPAAS_JOB_URL")},
    },
)

# 权限中心用户组申请链接
BK_IAM_USER_GROUP_APPLY_TMPL = BK_IAM_URL + "/apply-join-user-group?id={user_group_id}"

# 应用移动端访问地址，用于渲染模板与内置环境变量的配置项
BKPAAS_WEIXIN_URL_MAP = settings.get(
    "BKPAAS_WEIXIN_URL_MAP",
    {
        "stag": "http://localhost:8080/",
        "prod": "http://localhost:8080/",
    },
)
# 应用移动端允许的域名后缀，如果为空列表，允许任意域名
MOBILE_DOAMIN_SUFFIXS = settings.get("MOBILE_DOAMIN_SUFFIXS", [".example.com"])

# 统一登录页面地址，用于模板渲染与内置环境变量的配置项
LOGIN_FULL = settings.get("LOGIN_FULL", f"{BK_PAAS2_URL}/login/")
LOGIN_SIMPLE = settings.get("LOGIN_SIMPLE", f"{BK_PAAS2_URL}/login/plain/")

# 蓝鲸统一登录服务地址，用于平台登录
BK_LOGIN_API_URL = settings.get("BK_LOGIN_API_URL", LOGIN_FULL)

# 蓝鲸桌面访问地址，用于内置环境变量
BK_CONSOLE_URL = settings.get("BK_CONSOLE_URL", f"{BK_PAAS2_URL}/console/")

# 用于测试的无意义的应用 template 名称
DUMMY_TEMPLATE_NAME = "dummy_template"

# 默认 Region 名称
DEFAULT_REGION_NAME = settings.get("DEFAULT_REGION_NAME", "default")

DEFAULT_REGION_TEMPLATE = {
    "name": "default",
    "display_name": "默认版",
    "basic_info": {
        "description": "默认版",
        "link_production_app": BK_CONSOLE_URL + "?app={code}",
        "extra_logo_bucket_info": {},
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
    "enabled_feature_flags": [],
    # 应用是否需要写入蓝鲸体系其他系统访问地址的环境变量
    "provide_env_vars_platform": True,
}

REGION_CONFIGS = settings.get("REGION_CONFIGS", {"regions": [copy.deepcopy(DEFAULT_REGION_TEMPLATE)]})

# 蓝鲸 OAuth 服务地址（用于纳管蓝鲸应用 bk_app_code/bk_app_secret/）
BK_OAUTH_API_URL = settings.get("BK_OAUTH_API_URL", "http://localhost:8080")


# --------
# 用户鉴权模块 bkpaas_auth SDK 相关配置
# --------

# 解析通过 API Gateway 的请求，该值为空时跳过解析
APIGW_PUBLIC_KEY = settings.get("APIGW_PUBLIC_KEY", "")

# 是否启用多租户模式, 需要和 ENABLE_MULTI_TENANT_MODE 保持一致
BKAUTH_ENABLE_MULTI_TENANT_MODE = ENABLE_MULTI_TENANT_MODE

BKAUTH_DEFAULT_PROVIDER_TYPE = settings.get("BKAUTH_DEFAULT_PROVIDER_TYPE", "BK")
BKAUTH_BACKEND_TYPE = settings.get("BKAUTH_BACKEND_TYPE", "bk_token")
BKAUTH_TOKEN_APP_CODE = settings.get("BKAUTH_TOKEN_APP_CODE", BK_APP_CODE)
BKAUTH_TOKEN_SECRET_KEY = settings.get("BKAUTH_TOKEN_SECRET_KEY", BK_APP_SECRET)

# 如果当前环境没有 bk-login 网关，则设置 BKAUTH_USER_INFO_APIGW_URL 为空字符串, bkpaas_auth 将使用 BKAUTH_USER_COOKIE_VERIFY_URL
# 如果设置了有效的 BKAUTH_USER_INFO_APIGW_URL, BKAUTH_USER_COOKIE_VERIFY_URL 配置将被忽略, 使用网关进行用户身份校验
# 多租户模式下(BKAUTH_ENABLE_MULTI_TENANT_MODE=True)必须设置有效的 BKAUTH_USER_INFO_APIGW_URL, 否则无法使用租户功能
BKAUTH_BK_LOGIN_APIGW_STAGE = settings.get("BKAUTH_BK_LOGIN_APIGW_STAGE", "prod")
BKAUTH_USER_INFO_APIGW_URL = settings.get(
    "BKAUTH_USER_INFO_APIGW_URL",
    f"{BK_API_URL_TMPL.format(api_name='bk-login')}/{BKAUTH_BK_LOGIN_APIGW_STAGE}/login/api/v3/open/bk-tokens/userinfo/",
)
BKAUTH_USER_COOKIE_VERIFY_URL = settings.get("BKAUTH_USER_COOKIE_VERIFY_URL", f"{BK_LOGIN_API_URL}/api/v3/is_login/")

BKAUTH_TOKEN_USER_INFO_ENDPOINT = settings.get(
    "BKAUTH_TOKEN_USER_INFO_ENDPOINT", f"{BK_COMPONENT_API_URL}/api/c/compapi/v2/bk_login/get_user/"
)
BKAUTH_TOKEN_GRANT_ENDPOINT = settings.get("BKAUTH_TOKEN_GRANT_ENDPOINT")
BKAUTH_TOKEN_CHECK_ENDPOINT = settings.get("BKAUTH_TOKEN_CHECK_ENDPOINT")
BKAUTH_BK_LOGIN_DOMAIN = settings.get("BKAUTH_BK_LOGIN_DOMAIN")
BKAUTH_BK_LOGIN_PATH = settings.get("BKAUTH_BK_LOGIN_PATH", "/")

# [admin] 管理后台页面的人员选择器的数据接口地址
USER_SELECTOR_LIST_API = f"{BK_COMPONENT_API_URL}/api/c/compapi/v2/usermanage/fs_list_users/"

# 用户类型，默认为蓝鲸用户
USER_TYPE = settings.get("USER_TYPE", ProviderType.BK.value)
# 转换为枚举类型
USER_TYPE = ProviderType(USER_TYPE)

# ---------------
# 云 API 相关配置
# ---------------

# 获取应用态的 AccessToken 的 API 地址
TOKEN_AUTH_ENDPOINT = settings.get("TOKEN_AUTH_ENDPOINT", f"{BK_SSM_URL}/api/v1/auth/access-tokens")
TOKEN_REFRESH_ENDPOINT = settings.get("TOKEN_REFRESH_ENDPOINT", f"{BK_SSM_URL}/api/v1/auth/access-tokens/refresh")
AUTH_ENV_NAME = settings.get("AUTH_ENV_NAME", "prod")

# 请求 Token 服务所使用的默认 App Code 与 Secret
CLI_AUTH_CODE = settings.get("CLI_AUTH_CODE", "")
CLI_AUTH_SECRET = settings.get("CLI_AUTH_SECRET", "")


# === 插件应用相关
# 是否允许创建蓝鲸插件应用
IS_ALLOW_CREATE_BK_PLUGIN_APP = settings.get("IS_ALLOW_CREATE_BK_PLUGIN_APP", False)

# 是否开启插件开发功能
IS_ALLOW_PLUGIN_CENTER = settings.get("IS_ALLOW_PLUGIN_CENTER", False)

# 管理插件应用的 API 网关时所使用的配置：
BK_PLUGIN_APIGW_SERVICE_STAGE = settings.get("BK_PLUGIN_APIGW_SERVICE_STAGE", "prod")  # 环境（stage）
BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE = settings.get("BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE", "default")  # 用户类型

# 插件仓库的可见范围:私有项目 visibility_level = 0; 公共项目 visibility_level = 10
PLUGIN_VISIBILTY_LEVEL = settings.get("PLUGIN_VISIBILTY_LEVEL", 10)

# -------------
# 引擎相关配置项
# -------------

# === 环境变量相关配置
#
# 系统环境变量使用的前缀
CONFIGVAR_SYSTEM_PREFIX = "BKPAAS_"
# 环境变量保留字段列表
CONFIGVAR_PROTECTED_NAMES = (
    "SLUG_URL",
    "HOME",
    "S3CMD_CONF",
    "HOSTNAME",
)
# 环境变量保留前缀列表
CONFIGVAR_PROTECTED_PREFIXES = settings.get("CONFIGVAR_PROTECTED_PREFIXES", ["BKPAAS_", "KUBERNETES_"])

# 用于校验内部服务间请求的 JWT 配置，携带用以下任何一个 key 签名的 JWT 的请求会被认为有效
PAAS_SERVICE_JWT_CLIENTS = get_paas_service_jwt_clients(settings)

# 应用构件包所使用对象存储配置
# Bucket 名称：保存应用源码包、初始化代码
BLOBSTORE_BUCKET_APP_SOURCE = settings.get("BLOBSTORE_BUCKET_APP_SOURCE", "bkpaas3-slug-packages")
# Bucket 名称：保存应用模板代码
BLOBSTORE_BUCKET_TEMPLATES = settings.get("BLOBSTORE_BUCKET_TEMPLATES", "bkpaas3-apps-tmpls")
# Bucket 名称：存储源码包
BLOBSTORE_BUCKET_AP_PACKAGES = settings.get("BLOBSTORE_BUCKET_AP_PACKAGES", "bkpaas3-source-packages")

# S-Mart 应用默认增强服务配置信息
SMART_APP_DEFAULT_SERVICES_CONFIG = settings.get("SMART_APP_DEFAULT_SERVICES_CONFIG", {"mysql": {}})


# 针对 slug 环境对敏感信息加密密钥
SLUG_ENCRYPT_SECRET_KEY = settings.get("SLUG_ENCRYPT_SECRET_KEY", BKKRILL_ENCRYPT_SECRET_KEY)


# 默认进程规格套餐名称
DEFAULT_PROC_SPEC_PLAN = "Starter"
PREMIUM_PROC_SPEC_PLAN = "4C2G5R"
ULTIMATE_PROC_SPEC_PLAN = "4C4G5R"


# 应用副本数相关配置：

# 按照进程名称与环境，配置默认副本数
ENGINE_PROC_REPLICAS_BY_TYPE = {
    # （进程类型, 环境名称）： 副本数量
    ("web", "stag"): 1,
    ("web", "prod"): 2,
}

# 如果应用源码打包后超过该尺寸，打印警告信息
ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB = 300

# 可恢复下架操作的最长时限
ENGINE_OFFLINE_RESUMABLE_SECS = 60


# == 应用运行时相关配置
#
# 默认运行时镜像名称
DEFAULT_RUNTIME_IMAGES = settings.get("DEFAULT_RUNTIME_IMAGES", "blueking")

# ------------------
# CI 相关配置
# ------------------

# 代码检查配置
CODE_CHECK_CONFIGS = settings.get("CODE_CHECK_CONFIGS", {})

# 开发者中心在蓝盾的项目 ID
BK_CI_PAAS_PROJECT_ID = settings.get("BK_CI_PAAS_PROJECT_ID", "bk_paas3")
# 云原生应用构建流水线 ID
BK_CI_BUILD_PIPELINE_ID = settings.get("BK_CI_BUILD_PIPELINE_ID", "")
# 云原生应用构建流水线调用用户（应使用虚拟账号）
BK_CI_CLIENT_USERNAME = settings.get("BK_CI_CLIENT_USERNAME", "blueking")

# ------------
# 增强服务相关
# ------------

# 各本地增强服务 vendor 基础配置
SERVICES_VENDOR_CONFIGS: Dict[str, Dict] = settings.get("SERVICES_VENDOR_CONFIGS", {})

# 后端轮询任务：刷新远程增强服务信息 - 默认轮询间隔
REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES = 5

# 是否禁用定时任务调度器
DISABLE_PERIODICAL_JOBS = settings.get("DISABLE_PERIODICAL_JOBS", False)

# 默认远程服务配置
SERVICE_REMOTE_ENDPOINTS: List[Dict] = get_service_remote_endpoints(settings)

# Transform to basic data type instead of using BoxList directly to avoid not pickle-able bug
# See: paasng/paasng/dev_resources/servicehub/remote/store.py for more information
if hasattr(SERVICE_REMOTE_ENDPOINTS, "to_list"):
    SERVICE_REMOTE_ENDPOINTS = SERVICE_REMOTE_ENDPOINTS.to_list()

# ---------------
# 应用市场相关配置
# ---------------

BK_CONSOLE_DBCONF = get_database_conf(
    settings, encrypted_url_var="PAAS_LEGACY_DATABASE_URL", env_var_prefix="BK_CONSOLE_", for_tests=RUNNING_TESTS
)

# 是否需要填写应用联系人
APP_REQUIRE_CONTACTS = settings.get("APP_REQUIRE_CONTACTS", False)

# --------------
# 平台日志相关配置
# --------------

# 是否将 PaaS API 请求日志发送给 Redis 队列
PAAS_API_LOG_REDIS_HANDLER = settings.get(
    "PAAS_API_LOG_REDIS_HANDLER",
    {
        # 开关，默认不发送
        "enabled": False,
        "url": "redis://localhost:6379/0",
        "queue_name": "paas_ng-meters",
        "tags": [],
    },
)


# --------------
# 应用日志相关配置
# --------------
# 默认的日志采集器类型, 可选值 "ELK", "BK_LOG"
# 低于 k8s 1.12 的集群不支持蓝鲸日志平台采集器, 如需要支持 k8s 1.12 版本(含) 以下集群, 默认值不能设置成 BK_LOG
LOG_COLLECTOR_TYPE = settings.get("LOG_COLLECTOR_TYPE", "ELK")
# 蓝鲸日志平台的 API 是否已经注册在 APIGW，未注册则走 ESB 调用日志平台 API
ENABLE_BK_LOG_APIGW = settings.get("ENABLE_BK_LOG_APIGW", True)
# 蓝鲸日志平台网关的环境，仅在 ENABLE_BK_LOG_APIGW=True 时生效
BK_LOG_APIGW_SERVICE_STAGE = settings.get("BK_LOG_APIGW_SERVICE_STAGE", "stag")
# 蓝鲸日志平台相关的配置项
BKLOG_TIME_ZONE = settings.get("BKLOG_TIME_ZONE")
BKLOG_STORAGE_CLUSTER_ID = settings.get("BKLOG_STORAGE_CLUSTER_ID")
BKLOG_CONFIG = settings.get(
    "BKLOG_CONFIG", {"TIME_ZONE": BKLOG_TIME_ZONE, "STORAGE_CLUSTER_ID": BKLOG_STORAGE_CLUSTER_ID}
)

# 日志 ES 服务地址
ELASTICSEARCH_HOSTS = settings.get(
    "ELASTICSEARCH_HOSTS", [{"host": "localhost", "port": "9200", "http_auth": "admin:blueking"}]
)

# 日志 ES 搜索超时时间
DEFAULT_ES_SEARCH_TIMEOUT = 30

# 日志 Index 名称模式
ES_K8S_LOG_INDEX_PATTERNS = settings.get("ES_K8S_LOG_INDEX_PATTERNS", "app_log-*")
# 接入层日志 Index 名称模式
ES_K8S_LOG_INDEX_NGINX_PATTERNS = settings.get("ES_K8S_LOG_INDEX_NGINX_PATTERNS", "app_log-nginx-(?P<date>.+)")

# 不允许查询日志的关键词
ES_JSON_FIELD_BLACKLIST = ["json.message", "json.asctime", "json.process"]
# 日志高亮标签，用于前端高亮显示结果
BK_LOG_HIGHLIGHT_TAG = ("[bk-mark]", "[/bk-mark]")


# ---------------
# 访问控制相关配置
# ---------------

# [region-aware] 访问控制主配置
ACCESS_CONTROL_CONFIG = settings.get(
    "ACCESS_CONTROL_CONFIG",
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

PAAS_ANALYSIS_BASE_URL = settings.get("PAAS_ANALYSIS_BASE_URL", "http://localhost:8085")
PAAS_ANALYSIS_JWT_CONF = settings.get("PAAS_ANALYSIS_JWT_CONF", {})


# ---------------
# 搜索服务相关配置
# ---------------

# 腾讯 iwiki 服务相关配置
IWIKI_WEB_UI_BASE_URL = settings.get("IWIKI_WEB_UI_BASE_URL", "http://localhost:8080")
IWIKI_API_BASE_URL = settings.get("IWIKI_API_BASE_URL", "http://localhost:8080")
IWIKI_API_RIO_GW_TOKEN = settings.get("IWIKI_API_RIO_GW_TOKEN", "")

# 腾讯码客相关配置
MK_SEARCH_API_BASE_URL = settings.get("MK_SEARCH_API_BASE_URL", "http://localhost:8080")
MK_SEARCH_API_RIO_GW_TOKEN = settings.get("MK_SEARCH_API_RIO_GW_TOKEN", "")
MK_SEARCH_API_PRIVATE_TOKEN = settings.get("MK_SEARCH_API_PRIVATE_TOKEN", "")


# ---------------
# 应用一键迁移配置
# ---------------
# 一键迁移超时时间
LEGACY_APP_MIGRATION_PROCESS_TIMEOUT = 600

# 一键迁移部署超时时间
LEGACY_APP_MIGRATION_DEPLOY_TIMEOUT = 1200

# 迁移超期未完成提醒，天数，超过期限后每次正式部署都有弹框提醒
MIGRATION_REMIND_DAYS = 7

# 迁移时，是否 patch 用户代码
IS_PATCH_CODE_IN_MGRLEGACY = settings.get("IS_PATCH_CODE_IN_MGRLEGACY", True)


# ------------------
# 蓝鲸文档中心配置
# ------------------
# 蓝鲸PaaS3.0资料库地址
BKDOC_URL = settings.get("BKDOC_URL", "http://localhost:8080")

# 文档应用的应用ID
BK_DOC_APP_ID = settings.get("BK_DOC_APP_ID", "bk_docs_center")

BK_DOCS_URL_PREFIX = settings.get("BK_DOCS_URL_PREFIX", "https://bk.tencent.com/docs")

# PaaS 产品文档版本号，社区版年度大版本更新后需要更新对应的文档版本号
BK_PAAS_DOCS_VER = settings.get("BK_PAAS_DOCS_VER", "1.5")

# PaaS 产品文档前缀，蓝鲸文档中心最新的方案需要各个产品自己添加语言、版本号
PAAS_DOCS_URL_PREFIX = f"{BK_DOCS_URL_PREFIX}/markdown/ZH/PaaS/{BK_PAAS_DOCS_VER}"

# 平台FAQ 地址
PLATFORM_FAQ_URL = settings.get("PLATFORM_FAQ_URL", f"{PAAS_DOCS_URL_PREFIX}/BaseGuide/faq")

# 是否有人工客服
SUPPORT_LIVE_AGENT = settings.get("SUPPORT_LIVE_AGENT", False)
# 人工客服配置
LIVE_AGENT_CONFIG = settings.get("LIVE_AGENT_CONFIG", {"text": "联系客服", "link": "about:blank"})

# 是否开启终端色彩
COLORFUL_TERMINAL_OUTPUT = True

# ------------------
# S-Mart 应用镜像化配置
# ------------------

# S-Mart 镜像仓库的 Registry 的域名
SMART_DOCKER_REGISTRY_HOST = settings.get("SMART_DOCKER_REGISTRY_ADDR", "index.docker.io")
# S-Mart 镜像仓库的命名空间, 即在 Registry 中的项目名
SMART_DOCKER_REGISTRY_NAMESPACE = settings.get("SMART_DOCKER_NAMESPACE", "bkpaas/docker")
# 用于访问 Registry 的账号
SMART_DOCKER_REGISTRY_USERNAME = settings.get("SMART_DOCKER_USERNAME", "bkpaas")
# 用于访问 Registry 的密码
SMART_DOCKER_REGISTRY_PASSWORD = settings.get("SMART_DOCKER_PASSWORD", "blueking")
# S-Mart 基础镜像信息
_SMART_TAG_SUFFIX = "smart"
SMART_IMAGE_NAME = f"{SMART_DOCKER_REGISTRY_NAMESPACE}/slug-pilot"
SMART_IMAGE_TAG = f"{parse_image(settings.get('APP_IMAGE', '')).tag or 'latest'}-{_SMART_TAG_SUFFIX}"
SMART_CNB_IMAGE_NAME = f"{SMART_DOCKER_REGISTRY_NAMESPACE}/run-heroku-bionic"
SMART_CNB_IMAGE_TAG = f"{parse_image(settings.get('HEROKU_RUNNER_IMAGE', '')).tag or 'latest'}-{_SMART_TAG_SUFFIX}"

# slugbuilder build 的超时时间, 单位秒
BUILD_PROCESS_TIMEOUT = int(settings.get("BUILD_PROCESS_TIMEOUT", 60 * 15))

# ------------------
# App 应用镜像仓库配置
# ------------------
# App 镜像仓库的 Registry 的域名
APP_DOCKER_REGISTRY_HOST = settings.get("APP_DOCKER_REGISTRY_ADDR", "index.docker.io")
# 是否跳过校验 App 镜像仓库的证书
APP_DOCKER_REGISTRY_SKIP_TLS_VERIFY = settings.get("APP_DOCKER_REGISTRY_SKIP_TLS_VERIFY", False)
# App 镜像仓库的命名空间, 即在 Registry 中的项目名
APP_DOCKER_REGISTRY_NAMESPACE = settings.get("APP_DOCKER_NAMESPACE", "bkpaas/docker")
# 用于访问 Registry 的账号
APP_DOCKER_REGISTRY_USERNAME = settings.get("APP_DOCKER_USERNAME", "bkpaas")
# 用于访问 Registry 的密码
APP_DOCKER_REGISTRY_PASSWORD = settings.get("APP_DOCKER_PASSWORD", "blueking")

# ------------------
# bk-lesscode 相关配置
# ------------------
# 是否允许创建 LessCode 应用
ENABLE_BK_LESSCODE = settings.get("ENABLE_BK_LESSCODE", True)
# bk_lesscode 注册在 APIGW 上的环境
BK_LESSCODE_APIGW_STAGE = settings.get("BK_LESSCODE_APIGW_STAGE", "prod")
# bk_lesscode 平台访问地址
BK_LESSCODE_URL = settings.get("BK_LESSCODE_URL", "")
BK_LESSCODE_TIPS = settings.get("BK_LESSCODE_TIPS", "")

# -----------------
# 源码托管相关配置项
# -----------------

DOCKER_REGISTRY_CONFIG = settings.get(
    "DOCKER_REGISTRY_CONFIG", {"DEFAULT_REGISTRY": "https://hub.docker.com", "ALLOW_THIRD_PARTY_REGISTRY": False}
)

# -----------------
# 插件开发中心配置项
# -----------------
# 插件中心「源码仓库」相关配置
PLUGIN_REPO_CONF = settings.get("PLUGIN_REPO_CONF")

# 插件开发中心在权限中心注册的系统 ID
IAM_PLUGINS_CENTER_SYSTEM_ID = settings.get("IAM_PLUGINS_CENTER_SYSTEM_ID", default="bk_plugins")

# 是否在开发者中心应用列表中展示插件应用
DISPLAY_BK_PLUGIN_APPS = settings.get("DISPLAY_BK_PLUGIN_APPS", True)

# 插件开发中心在蓝盾的项目 ID
PLUGIN_CENTER_PROJECT_ID = settings.get("PLUGIN_CENTER_PROJECT_ID", default="bkplugins")

# 插件开发者中心访问地址
PLUGIN_CENTER_URL = settings.get("PLUGIN_CENTER_URL", default=f"{BKPAAS_URL}/plugin-center")

# 插件应用的默认 LOGO
PLUGIN_APP_DEFAULT_LOGO = settings.get(
    "PLUGIN_APP_DEFAULT_LOGO", default=f"{BKPAAS_URL}/static/images/plugin-default.svg"
)

# -----------------
# 蓝鲸监控配置项
# -----------------
# 是否支持使用蓝鲸监控，影响：资源使用量、应用 metric 采集、告警策略下发、告警记录查询等功能
ENABLE_BK_MONITOR = settings.get("ENABLE_BK_MONITOR", False)
# 蓝鲸监控运维相关的额外配置
BKMONITOR_METRIC_RELABELINGS = settings.get("BKMONITOR_METRIC_RELABELINGS", [])
# 蓝鲸监控的API是否已经注册在 APIGW
ENABLE_BK_MONITOR_APIGW = settings.get("ENABLE_BK_MONITOR_APIGW", True)
# Rabbitmq 监控配置项, 格式如 {'enabled': True, 'metric_name_prefix': '', 'service_name': 'rabbitmq'}
RABBITMQ_MONITOR_CONF = settings.get("RABBITMQ_MONITOR_CONF", {})
# Bkrepo 监控配置项, 格式如 {'enabled': True, 'metric_name_prefix': '', 'service_name': 'bkrepo'}
BKREPO_MONITOR_CONF = settings.get("BKREPO_MONITOR_CONF", {})
# Gcs_mysql 监控配置项, 格式如 {'enabled': True, 'metric_name_prefix': '', 'service_name': 'gcs_mysql'}
GCS_MYSQL_MONITOR_CONF = settings.get("GCS_MYSQL_MONITOR_CONF", {})
# 蓝鲸监控网关的环境
BK_MONITOR_APIGW_SERVICE_STAGE = settings.get("BK_MONITOR_APIGW_SERVICE_STAGE", "stage")

# ---------------------------------------------
# 蓝鲸通知中心配置
# ---------------------------------------------
# 通知中心的功能可通过配置开启
ENABLE_BK_NOTICE = settings.get("ENABLE_BK_NOTICE", False)
# 对接通知中心的环境，默认为生产环境
BK_NOTICE_ENV = settings.get("BK_NOTICE_ENV", "prod")
BK_NOTICE = {
    "STAGE": BK_NOTICE_ENV,
    "LANGUAGE_COOKIE_NAME": LANGUAGE_COOKIE_NAME,
    "DEFAULT_LANGUAGE": "en",
    "PLATFORM": BK_APP_CODE,  # 平台注册的 code，用于获取系统通知消息时进行过滤
    "BK_API_URL_TMPL": BK_API_URL_TMPL,
    "BK_API_APP_CODE": BK_APP_CODE,  # 用于调用 apigw 认证
    "BK_API_SECRET_KEY": BK_APP_SECRET,  # 用于调用 apigw 认证
}

# ---------------------------------------------
# 蓝鲸审计中心配置
# ---------------------------------------------
# 审计中心-审计配置-接入-数据上报中获取这两项配置信息的值
BK_AUDIT_DATA_TOKEN = settings.get("BK_AUDIT_DATA_TOKEN", "")
BK_AUDIT_ENDPOINT = settings.get("BK_AUDIT_ENDPOINT", "")

ENABLE_BK_AUDIT = bool(BK_AUDIT_DATA_TOKEN)
BK_AUDIT_SETTINGS = {
    "log_queue_limit": 50000,
    "exporters": ["bk_audit.contrib.opentelemetry.exporters.OTLogExporter"],
    "service_name_handler": "bk_audit.contrib.opentelemetry.utils.ServiceNameHandler",
    "ot_endpoint": BK_AUDIT_ENDPOINT,
    "bk_data_token": BK_AUDIT_DATA_TOKEN,
}

# ---------------------------------------------
# 蓝鲸容器服务配置
# ---------------------------------------------
# 是否部署了 BCS，影响访问控制台等功能
ENABLE_BCS = settings.get("ENABLE_BCS", True)

# BCS 集群 Server URL 模板（用于 API 访问/ kubectl 配置）
BCS_CLUSTER_SERVER_URL_TMPL = settings.get(
    "BCS_CLUSTER_SERVER_URL_TMPL", f"http://bcs-api.{BK_DOMAIN}/clusters/{{cluster_id}}/"
)

# ---------------------------------------------
# （internal）内部配置，仅开发项目与特殊环境下使用
# ---------------------------------------------

FOR_TESTS_LEGACY_APP_CODE = settings.get("FOR_TESTS_LEGACY_APP_CODE", "test-app")
# 用于测试的真实可连接的 svn 服务器地址，如提供，将会在单元测试执行真实的 export 等操作
FOR_TESTS_SVN_SERVER_CONF = settings.get("FOR_TESTS_SVN_SERVER_CONF")
FOR_TESTS_APP_SVN_INFO = settings.get("FOR_TESTS_APP_SVN_INFO")

PAAS_X_BK_DATA_DB_CONF = settings.get("PAAS_X_BK_DATA_DB_CONF", {})
DEBUG_FORCE_DISABLE_CSRF = settings.get("DEBUG_FORCE_DISABLE_CSRF", False)

# Sentry 错误收集服务配置
SENTRY_CONFIG = settings.get("SENTRY_CONFIG", {})

# openTelemetry trace 配置，默认不启用
ENABLE_OTEL_TRACE = settings.get("ENABLE_OTEL_TRACE", False)
OTEL_INSTRUMENT_DB_API = settings.get("OTEL_INSTRUMENT_DB_API", True)
# 上报数据服务名称
OTEL_SERVICE_NAME = settings.get("OTEL_SERVICE_NAME", "bkpaas3-apiserver")
# sdk 采样规则（always_on / always_off / parentbased_always_on...）
OTEL_SAMPLER = settings.get("OTEL_SAMPLER", "always_on")
OTEL_BK_DATA_TOKEN = settings.get("OTEL_BK_DATA_TOKEN", "")
OTEL_GRPC_URL = settings.get("OTEL_GRPC_URL", "")

if ENABLE_OTEL_TRACE:
    INSTALLED_APPS += ("paasng.misc.tracing",)

# 本选项默认关闭。表示注入到应用运行环境中的 {prefix}_SUB_PATH 环境变量总是使用真实值（基于算法的最短子路径）。
# 开启后将总是使用静态值：{region}-{engine-app-name} ，仅限特殊路由规则的部署环境启用。
FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE = settings.get("FORCE_USING_LEGACY_SUB_PATH_VAR_VALUE", False)

# 是否启用格式为 `/{region}-{engine_app_name}/` 的子路径，仅供某些需向前兼容的特殊
# 环境下使用，默认关闭。
USE_LEGACY_SUB_PATH_PATTERN = settings.get("USE_LEGACY_SUB_PATH_PATTERN", False)

# 初始化的第三方应用(外链应用)的 code,多个以英文逗号分割
THIRD_APP_INIT_CODES = settings.get("THIRD_APP_INIT_CODES", "")

# 允许通过 API 创建第三方应用(外链应用)的系统ID,多个以英文逗号分割
ALLOW_THIRD_APP_SYS_IDS = settings.get("ALLOW_THIRD_APP_SYS_IDS", "")
ALLOW_THIRD_APP_SYS_ID_LIST = ALLOW_THIRD_APP_SYS_IDS.split(",") if ALLOW_THIRD_APP_SYS_IDS else []

# ---------------------------------------------
# 平台通知配置相关
# ---------------------------------------------

# 开发者中心管理员，主要用于应用运营报告通知
BKPAAS_PLATFORM_MANAGERS = settings.get("BKPAAS_PLATFORM_MANAGERS", [])
# 是否向平台管理员发送应用运营报告邮件
ENABLE_SEND_OPERATION_REPORT_EMAIL_TO_PLAT_MANAGE = settings.get(
    "ENABLE_SEND_OPERATION_REPORT_EMAIL_TO_PLAT_MANAGE", False
)

# 发送验证码，没有配置通知渠道的版本可以关闭该功能
ENABLE_VERIFICATION_CODE = settings.get("ENABLE_VERIFICATION_CODE", False)

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


# ---------------------------------------------
#  挂载卷相关配置
# ---------------------------------------------

# 持久存储默认存储类型
DEFAULT_PERSISTENT_STORAGE_CLASS_NAME = settings.get("DEFAULT_PERSISTENT_STORAGE_CLASS_NAME", "cfs")

# 持久存储默认存储大小
DEFAULT_PERSISTENT_STORAGE_SIZE = settings.get("DEFAULT_PERSISTENT_STORAGE_SIZE", "1Gi")


# ---------------------------------------------
#  前端特性配置
# ---------------------------------------------
# 应用市场可见范围
FE_FEATURE_SETTINGS_MARKET_VISIBILITY = settings.get("FE_FEATURE_SETTINGS_MARKET_VISIBILITY", True)
# 聚合搜索
FE_FEATURE_SETTINGS_AGGREGATE_SEARCH = settings.get("FE_FEATURE_SETTINGS_AGGREGATE_SEARCH", False)
# 文档管理功能
FE_FEATURE_SETTINGS_DOCUMENT_MANAGEMENT = settings.get("FE_FEATURE_SETTINGS_DOCUMENT_MANAGEMENT", False)
# 记录本地开发时长，部分版本的普通应用还有该功能
FE_FEATURE_SETTINGS_DEVELOPMENT_TIME_RECORD = settings.get("FE_FEATURE_SETTINGS_DEVELOPMENT_TIME_RECORD", False)
# 显示应用版本
FE_FEATURE_SETTINGS_REGION_DISPLAY = settings.get("FE_FEATURE_SETTINGS_REGION_DISPLAY", False)
# 用于控制前端页面是否展示访问统计功能
FE_FEATURE_SETTINGS_ANALYTICS = settings.get("FE_FEATURE_SETTINGS_ANALYTICS", False)
# 镜像应用绑定源码仓库，仅用于代码检查
FE_FEATURE_SETTINGS_IMAGE_APP_BIND_REPO = settings.get("FE_FEATURE_SETTINGS_IMAGE_APP_BIND_REPO", False)
# 是否开启应用迁移相关功能
FE_FEATURE_SETTINGS_MGRLEGACY = settings.get("FE_FEATURE_SETTINGS_MGRLEGACY", False)
# 是否开启迁移至云原生应用的相关功能（注：启用该特性需要配置 MGRLEGACY_CLOUD_NATIVE_TARGET_CLUSTER）
FE_FEATURE_SETTINGS_CNATIVE_MGRLEGACY = settings.get("FE_FEATURE_SETTINGS_CNATIVE_MGRLEGACY", False)
# 应用令牌，用于 APP 调用用户态的云 API
FE_FEATURE_SETTINGS_APP_ACCESS_TOKEN = settings.get("FE_FEATURE_SETTINGS_APP_ACCESS_TOKEN", False)
# 是否显示沙箱
FE_FEATURE_SETTINGS_DEV_SANDBOX = settings.get("FE_FEATURE_SETTINGS_DEV_SANDBOX", False)
# 是否展示应用可用性保障
FE_FEATURE_SETTINGS_APP_AVAILABILITY_LEVEL = settings.get("FE_FEATURE_SETTINGS_APP_AVAILABILITY_LEVEL", False)

# FORBIDDEN_REPO_PORTS 包含与代码/镜像仓库相关的敏感端口，配置后，平台将不允许用户填写或注册相关的代码/镜像仓库
FORBIDDEN_REPO_PORTS = settings.get("FORBIDDEN_REPO_PORTS", [])
