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

import logging
import os
from pathlib import Path

import environ
import pymysql
import sentry_sdk
import urllib3
from django.db.backends.mysql.features import DatabaseFeatures
from django.utils.functional import cached_property
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

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


env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# read `.env` from 'svc_otel/settings/.env'
env.read_env()

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Build paths inside the project like this: BASE_DIR / ...
BASE_DIR = Path(__file__).parents[2].absolute()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY", default="c6h~oz+!%4b%br^8ekz&s7zt$(athjh_")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

# 允许访问的域名
ALLOWED_HOSTS = ["*"]

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
    "svc_otel.vendor",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Append middlewares from paas_service to make client auth works
    "paas_service.auth.middleware.VerifiedClientMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

STATIC_ROOT = "staticfiles"

STATICFILES_DIRS = [
    str(BASE_DIR / "static"),
]

ROOT_URLCONF = "svc_otel.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "svc_otel/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "svc_otel.middleware.context_processors",
            ],
        },
    },
]

WSGI_APPLICATION = "svc_otel.wsgi.application"

# Database

if os.getenv("DATABASE_URL"):
    DATABASES = {"default": env.db()}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("MYSQL_NAME", default="svc_bkrepo"),
            "USER": env("MYSQL_USER", default="svc_bkrepo"),
            "PASSWORD": env("MYSQL_PASSWORD", default="blueking"),
            "HOST": env("MYSQL_HOST", default="127.0.0.1"),
            "PORT": env("MYSQL_PORT", default="3306"),
            "OPTIONS": env.json("MYSQL_OPTIONS", default={}),
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

# Internationalization

LANGUAGE_CODE = "zh-cn"

LANGUAGES = [("zh-cn", "简体中文"), ("en", "English")]

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGGING_LEVEL = "DEBUG"


def get_logging_config(log_level="DEBUG"):
    default_handlers = ["console"]
    handlers = {
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": log_level,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "%(levelname)s [%(asctime)s] %(name)s(ln:%(lineno)d): %(message)s",  # noqa
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {"format": "%(levelname)s %(message)s"},
        },
        "handlers": handlers,
        "loggers": {
            "root": {
                "handlers": default_handlers,
                "level": "INFO",
                "propagate": True,
            },
            "svc_otel": {
                "handlers": default_handlers,
                "level": "DEBUG",
                "propagate": True,
            },
            "django.request": {
                "handlers": default_handlers,
                "level": "ERROR",
                "propagate": False,
            },
            "": {
                "handlers": default_handlers,
                "level": "ERROR",
                "propagate": True,
            },
        },
    }


LOGGING = get_logging_config(LOGGING_LEVEL)

# 环境变量设置了 BKKRILL_ENCRYPT_SECRET_KEY 且不为空时才使用环境变量中的值，否则使用默认值
BKKRILL_ENCRYPT_SECRET_KEY = (
    env.str("BKKRILL_ENCRYPT_SECRET_KEY", default="").encode()
    or "b1ZPY1FDTXV1WGpGb0x2cmJKdlVLQW5OdnJBb2FscVY=".encode()
)


METRIC_CLIENT_TOKEN_DICT = {
    "monitoring": env.str("METRIC_CLIENT_TOKEN", "f7b58586-5e20-f189-7cf5-a020524cda3e"),
}

SENTRY_DSN = env.str("SENTRY_DSN", default="")

# 接入 sentry
# All of this is already happening by default!
sentry_logging = LoggingIntegration(
    level=logging.INFO,
    # Capture info and above as breadcrumbs
    # Send errors as events
    event_level=logging.ERROR,
)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), sentry_logging],
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )

# 增强服务供应商类
PAAS_SERVICE_PROVIDER_CLS = "svc_otel.vendor.provider.Provider"
# 增强服务方案配置 schema 类
PAAS_SERVICE_PLAN_SCHEMA_CLS = "svc_otel.vendor.schema.PlanSchema"
# 增强服务实例信息渲染函数
PAAS_SERVICE_SVC_INSTANCE_RENDER_FUNC = "svc_otel.vendor.render.render_instance_data"

PAAS_SERVICE_JWT_CLIENTS = [
    {
        "iss": "paas-v3",
        "key": env.str("PAAS_SERVICE_JWT_CLIENTS_KEY"),
        "algorithm": "HS256",
    },
]

# 是否开启管理端功能
ENABLE_ADMIN = True

# 跳转回应用首页的 url 模板
DEVELOPER_CENTER_APP_URL_TEMPLATE = "http://your-paas3.0-host/developer-center/apps/{app_code}/{module}/summary"

# 在监控获取的grpc push url
BK_OTEL_GRPC_URL = env("BK_OTEL_GRPC_URL", default="")
# 调用 API 需要的信息
BK_APP_CODE = env("BK_APP_CODE", default="bk_paas3")
BK_APP_SECRET = env("BK_APP_SECRET", default="")
# 对外版蓝鲸监控的 API 注册在 ESB
BK_COMPONENT_API_URL = env("BK_COMPONENT_API_URL", default="")
# 上云版蓝鲸监控的 API 注册在 APIGW
BK_API_URL_TMPL = env("BK_API_URL_TMPL", default="")
APIGW_ENVIRONMENT = env("APIGW_ENVIRONMENT", default="prod")
# 蓝鲸监控的API是否已经注册在 APIGW
ENABLE_BK_MONITOR_APIGW = env.bool("ENABLE_BK_MONITOR_APIGW", default=True)
# 蓝鲸监控的访问地址, 用于拼接 APM 详情页面的访问地址
BK_MONITORV3_URL = env("BK_MONITORV3_URL", default="")

# 选择加密数据库内容的算法，可选择：'SHANGMI' , 'CLASSIC'
BK_CRYPTO_TYPE = env.str("BK_CRYPTO_TYPE", default="CLASSIC")
ENCRYPT_CIPHER_TYPE = "SM4CTR" if BK_CRYPTO_TYPE == "SHANGMI" else "FernetCipher"
