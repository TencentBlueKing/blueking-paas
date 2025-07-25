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

import os

import environ
import pymysql
import urllib3
from django.db.backends.mysql.features import DatabaseFeatures
from django.utils.functional import cached_property

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
# Patch version info to force pass Django client check
setattr(pymysql, "version_info", (1, 4, 6, "final", 0))

env = environ.Env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY", "t4kiak&jPl0!bvHNEyxmJSsO4DEpqH9Z")

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = env.bool("DEBUG", False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "paas_service",
    "vendor",
    "tasks",
    "monitor",
]

SENTRY_DSN = env.str("SENTRY_DSN", "")
if SENTRY_DSN:
    INSTALLED_APPS.append("raven.contrib.django.raven_compat")
    RAVEN_CONFIG = {
        "dsn": SENTRY_DSN,
    }

MIDDLEWARE = [
    # "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Append middlewares from paas_service to make client auth works
    "paas_service.auth.middleware.VerifiedClientMiddleware",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = "svc_rabbitmq.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "svc_rabbitmq.middleware.context_processors",
            ],
        },
    },
]

WSGI_APPLICATION = "svc_rabbitmq.wsgi.application"

# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env.str("MYSQL_NAME", "service_rabbitmq"),
        "USER": env.str("MYSQL_USER", "service_rabbitmq"),
        "PASSWORD": env.str("MYSQL_PASSWORD"),
        "HOST": env.str("MYSQL_HOST", "localhost"),
        "PORT": env.str("MYSQL_PORT", "3306"),
        "OPTIONS": env.json("MYSQL_OPTIONS", {}),
    }
}

# Password validation

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

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Internationalization

LANGUAGE_CODE = "zh-cn"

LANGUAGES = [("zh-cn", "简体中文"), ("en", "English")]

TIME_ZONE = env.str("TIME_ZONE", "UTC")

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOG_LEVEL = env.str("LOG_LEVEL", "INFO")
LOG_FILE = env.str("LOG_FILE", "")

LOG_NULL_HANDLER = "svc_rabbitmq.log.NullHandler"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(name)s %(levelname)s [%(asctime)s] %(name)s(ln:%(lineno)d): %(message)s",  # noqa
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "sentry": {
            "level": "ERROR",
            "class": ("raven.handlers.logging.SentryHandler" if SENTRY_DSN else LOG_NULL_HANDLER),
            "dsn": SENTRY_DSN,
        },
        "file": {
            "level": "DEBUG",
            "class": ("logging.handlers.WatchedFileHandler" if LOG_FILE else LOG_NULL_HANDLER),
            "formatter": "verbose",
            "filename": LOG_FILE,
        },
    },
    "loggers": {
        logger_name: {
            "handlers": ["console", "file", "sentry"],
            "level": LOG_LEVEL,
            "propagate": False,
        }
        for logger_name in [
            "root",
            "django.request",
            "django.server",
            "svc_rabbitmq",
            "vendor",
            "paas_service",
            "tasks",
        ]
    },
}

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static_files")
STATICFILES_DIRS = []

BKKRILL_ENCRYPT_SECRET_KEY = env.bytes("BKKRILL_ENCRYPT_SECRET_KEY")
METRIC_CLIENT_TOKEN_DICT = {
    env.str("MONITOR_METRIC_CLIENT", "monitoring"): env.str("MONITOR_METRIC_TOKEN", ""),
}

PAAS_SERVICE_PROVIDER_CLS = "vendor.provider.Provider"
PAAS_SERVICE_PLAN_SCHEMA_CLS = "vendor.schema.PlanSchema"
PAAS_SERVICE_JWT_CLIENTS = [
    {
        "iss": env.str("PAAS_SERVICE_JWT_CLIENTS_ISS", "paas-v3"),
        "key": env.str("PAAS_SERVICE_JWT_CLIENTS_KEY"),
        "algorithm": env.str("PAAS_SERVICE_JWT_CLIENTS_ALGORITHM", "HS256"),
    },
]
PAAS_SERVICE_SVC_INSTANCE_RENDER_FUNC = "vendor.render.render_instance_data"

INSTANCE_APP_NAME_MAX_LENGTH = env.int("INSTANCE_APP_NAME_MAX_LENGTH", 16)
INSTANCE_BILL_ID_MAX_LENGTH = env.int("INSTANCE_BILL_ID_MAX_LENGTH", 4)
INSTANCE_DEFAULT_PREFIX = env.str("INSTANCE_DEFAULT_PREFIX", "app")

RABBITMQ_DEFAULT_USER_TAGS = env.str("RABBITMQ_DEFAULT_USER_TAGS", "management")  # 逗号分隔
RABBITMQ_DEFAULT_USER_CONFIGURE_PERMISSIONS = env.str("RABBITMQ_DEFAULT_USER_CONFIGURE_PERMISSIONS", ".*")
RABBITMQ_DEFAULT_USER_WRITE_PERMISSIONS = env.str("RABBITMQ_DEFAULT_USER_WRITE_PERMISSIONS", ".*")
RABBITMQ_DEFAULT_USER_READ_PERMISSIONS = env.str("RABBITMQ_DEFAULT_USER_READ_PERMISSIONS", ".*")
RABBITMQ_DEFAULT_DEAD_LETTER_ROUTING_KEY = env.str("RABBITMQ_DEFAULT_DEAD_LETTER_ROUTING_KEY", "")
RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE = env.str("RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE", "dlx.exchange")
RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_TYPE = env.str("RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_TYPE", "direct")
RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_DURABLE = env.bool("RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_DURABLE", False)
RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE = env.str("RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE", "dlx.queue")
RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE_DURABLE = env.bool("RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE_DURABLE", False)
RABBITMQ_MANAGEMENT_API_CACHE_SECONDS = env.int("RABBITMQ_MANAGEMENT_API_CACHE_SECONDS", 3)

MODEL_TAG_CLUSTER = "cluster"

CACHES = {
    "database": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": env.str("CACHE_TABLE_NAME", "cache_table"),
    },
}

CACHES["default"] = CACHES[env.str("CACHE_BACKEND", "database")]

# 秒
CRON_TASK_CHECK_INTERVAL = env.int("CRON_TASK_CHECK_INTERVAL", 10)

# 分钟
RABBITMQ_CLUSTER_ALIVE_CHECK_INTERVAL = env.int("RABBITMQ_CLUSTER_ALIVE_CHECK_INTERVAL", 5)
RABBITMQ_INSTANCE_ALIVE_CHECK_INTERVAL = env.int("RABBITMQ_INSTANCE_ALIVE_CHECK_INTERVAL", 5)
RABBITMQ_INSTANCE_VHOST_CHECK_INTERVAL = env.int("RABBITMQ_INSTANCE_VHOST_CHECK_INTERVAL", 5)
RABBITMQ_INSTANCE_QUEUE_CHECK_INTERVAL = env.int("RABBITMQ_INSTANCE_QUEUE_CHECK_INTERVAL", 5)
RABBITMQ_CONNECTION_RECOVERY_INTERVAL = env.int("RABBITMQ_CONNECTION_RECOVERY_INTERVAL", 60)
RABBITMQ_CONNECTION_RECOVERY_MAX_IDLE = env.int("RABBITMQ_CONNECTION_RECOVERY_MAX_IDLE", 7200)

MAX_TASK_WORKERS = env.int("MAX_TASK_WORKERS", 2)
MAX_TASK_PRE_WORKER = env.int("MAX_TASK_PRE_WORKER", 100)

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

SCHEDULER_ENABLED = env.bool("SCHEDULER_ENABLED", False)

FEATURE_FLAG_ENABLE_ADMIN = env.bool("FEATURE_FLAG_ENABLE_ADMIN", False)

REMOTE_LOGO_URL = env.str("REMOTE_LOGO_URL", "")

# 迁移的实例默认的集群
INSTANCE_DEFAULT_CLUSTER_ID = env.int("INSTANCE_DEFAULT_CLUSTER_ID", 0)

# 选择加密数据库内容的算法，可选择：'SHANGMI' , 'CLASSIC'
BK_CRYPTO_TYPE = env.str("BK_CRYPTO_TYPE", default="CLASSIC")
ENCRYPT_CIPHER_TYPE = "SM4CTR" if BK_CRYPTO_TYPE == "SHANGMI" else "FernetCipher"
