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
import base64
import os
from pathlib import Path

import environ

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# read `.env` from 'svc_otel/settings/.env'
env.read_env()

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Build paths inside the project like this: BASE_DIR / ...
BASE_DIR = Path(__file__).parents[2].absolute()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'c6h~oz+!%4b%br^8ekz&s7zt$(athjh_'

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
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATIC_URL = "/static/"

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
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

if os.getenv("DATABASE_URL"):
    DATABASES = {"default": env.db()}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            "NAME": env("MYSQL_NAME", default="svc_bkrepo"),
            "USER": env("MYSQL_USER", default="svc_bkrepo"),
            "PASSWORD": env("MYSQL_PASSWORD", default="blueking"),
            "HOST": env("MYSQL_HOST", default="127.0.0.1"),
            "PORT": env("MYSQL_PORT", default=3306),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'zh-cn'

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


BKKRILL_ENCRYPT_SECRET_KEY = base64.b64encode(b'oVOcQCMuuXjFoLvrbJvUKAnNvrAoalqV')

METRIC_CLIENT_TOKEN_DICT = {
    "monitoring": env.str("METRIC_CLIENT_TOKEN", "f7b58586-5e20-f189-7cf5-a020524cda3e"),
}

SENTRY_DSN = env.str("SENTRY_DSN", default="")

# 增强服务供应商类
PAAS_SERVICE_PROVIDER_CLS = "svc_otel.vendor.provider.Provider"
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
ENABLE_ADMIN = False

# 跳转回应用首页的 url 模板
DEVELOPER_CENTER_APP_URL_TEMPLATE = "http://your-paas3.0-host/developer-center/apps/{app_code}/{module}/summary"

# 在监控获取的grpc push url
BK_OTEL_GRPC_URL = env("BK_OTEL_GRPC_URL", default='')
# 调用 API 需要的信息
BK_COMPONENT_API_URL = env("BK_COMPONENT_API_URL", default='')
BK_APP_CODE = env("BK_APP_CODE", default='bk_paas3')
BK_APP_SECRET = env("BK_APP_SECRET", default='')
