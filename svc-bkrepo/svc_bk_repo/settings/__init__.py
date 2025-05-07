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

env.read_env()

# Build paths inside the project like this: BASE_DIR / ...
BASE_DIR = Path(__file__).parents[2].absolute()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY", default="ot08tcs_&u(&fb~bgny!6+(b07ch*@nj")

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
    "svc_bk_repo.vendor",
    "bkpaas_auth",
    "svc_bk_repo.monitoring",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "bkpaas_auth.middlewares.CookieLoginMiddleware",
    # Append middlewares from paas_service to make client auth works
    "paas_service.auth.middleware.VerifiedClientMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
REMOTE_STATIC_URL = "/static/"

STATIC_ROOT = "staticfiles"

STATICFILES_DIRS = [
    str(BASE_DIR / "static"),
]

ROOT_URLCONF = "svc_bk_repo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "svc_bk_repo/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "svc_bk_repo.middleware.context_processors",
            ],
        },
    },
]

WSGI_APPLICATION = "svc_bk_repo.wsgi.application"

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
            "svc_bk_repo": {
                "handlers": default_handlers,
                "level": "DEBUG",
                "propagate": True,
            },
            "django.request": {
                "handlers": default_handlers,
                "level": "ERROR",
                "propagate": False,
            },
        },
    }


LOGGING = get_logging_config(LOGGING_LEVEL)

BKKRILL_ENCRYPT_SECRET_KEY = env.str(
    "BKKRILL_ENCRYPT_SECRET_KEY", default="U2ViQ1dRc0FiSU9jaFBhd0p0emhZQmhxRHpDdGdxU1k="
).encode()

METRIC_CLIENT_TOKEN_DICT = {
    "monitoring": env.str("METRIC_CLIENT_TOKEN", "2892bd51-9a21-29f2-be21-ab6278108317"),
}

BKREPO_COLLECT_INTERVAL_MINUTES = env.int("BKREPO_COLLECT_INTERVAL_MINUTES", default=30)

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
PAAS_SERVICE_PROVIDER_CLS = "svc_bk_repo.vendor.provider.Provider"
# 增强服务实例信息渲染函数
PAAS_SERVICE_SVC_INSTANCE_RENDER_FUNC = "svc_bk_repo.vendor.render.render_instance_data"

PAAS_SERVICE_JWT_CLIENTS = [
    {
        "iss": "paas-v3",
        "key": env.str("PAAS_SERVICE_JWT_CLIENTS_KEY"),
        "algorithm": "HS256",
    },
]

# 是否开启管理端功能
ENABLE_ADMIN = env.bool("ENABLE_ADMIN", False)

# 跳转回应用首页的 url 模板
DEVELOPER_CENTER_APP_URL_TEMPLATE = "http://your-paas3.0-host/developer-center/apps/{app_code}/{module}/summary"

# bkrepo 默认配额, 单位字节
BKREPO_DEFAULT_QUOTA = env.int("BKREPO_DEFAULT_QUOTA", None)

# bkrepo 扩容最大容量限制, 10g, 单位 bytes
EXTEND_CONFIG_MAX_SIZE_ALLOWED = 2**30 * 10

# bkrepo 扩容步长, 1g, 单位 bytes
EXTEND_CONFIG_EXTRA_SIZE_BYTES = 2**30

BKAUTH_DEFAULT_PROVIDER_TYPE = env("BKAUTH_DEFAULT_PROVIDER_TYPE", default="BK")
# 蓝鲸登录票据在Cookie中的名称，权限中心 API 未接入 APIGW，访问时需要提供登录态信息
BKAUTH_BACKEND_TYPE = env("BKAUTH_BACKEND_TYPE", default="bk_token")

LOGIN_URL = env.str("BK_LOGIN_API_URL", default="http://paasee.blueking-fake.com/login")

BKAUTH_USER_COOKIE_VERIFY_URL = LOGIN_URL + env.str("BK_LOGIN_VERIFY_API_PATH", default="/api/v3/is_login/")

AUTHENTICATION_BACKENDS = [
    # [推荐] 使用内置的虚拟用户类型，不依赖于数据库表.
    # 'bkpaas_auth.backends.UniversalAuthBackend',
    # 如果项目需要保留使用数据库表的方式来设计用户模型, 则需要使用 DjangoAuthUserCompatibleBackend
    "bkpaas_auth.backends.DjangoAuthUserCompatibleBackend",
]

# 选择加密数据库内容的算法，可选择：'SHANGMI' , 'CLASSIC'
BK_CRYPTO_TYPE = env.str("BK_CRYPTO_TYPE", default="CLASSIC")
ENCRYPT_CIPHER_TYPE = "SM4CTR" if BK_CRYPTO_TYPE == "SHANGMI" else "FernetCipher"
