# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""app-spark-api settings.

默认情况下，本项目会读取根目录（manage.py 所在目录）下的 `settings_files` 子目录内的所有
YAML 文件和 `settings_local.yaml` 的内容，将其作为配置项使用。你也可以用
`APP_SPARK_API_SETTINGS` 环境变量指定其他配置文件，比如：

    # 多个配置文件使用 ; 分割
    export APP_SPARK_API_SETTINGS='common.yaml;dev.yaml'

指定其他文件后，`settings_files/*.yaml` 与 `settings_local.yaml` 仍然会生效，最终
配置会是所有内容合并后的结果。

除了 YAML 外，每个配置项也可通过环境变量设置。比如，在 YAML 文件里的配置项 `SECRET_KEY: foo`，
也可使用以下环境变量修改：

    export APP_SPARK_API_SECRET_KEY='foo'

注意事项：

- 必须添加 `APP_SPARK_API_` 前缀
- 环境变量比 YAML 配置的优先级更高
- 环境变量可修改字典内的嵌套值，参考文档：https://www.dynaconf.com/envvars/
"""

from pathlib import Path

import pymysql
from dynaconf import LazySettings

from .utils import get_database_conf

pymysql.install_as_MySQLdb()


BASE_DIR = Path(__file__).resolve().parents[2]

# 默认加载的额外配置文件，主要用于本地开发
SETTINGS_FILES_GLOB = str(BASE_DIR / "settings_files/*.yaml")
LOCAL_SETTINGS = str(BASE_DIR / "settings_local.yaml")

settings = LazySettings(
    environments=False,
    load_dotenv=True,
    includes=[SETTINGS_FILES_GLOB, LOCAL_SETTINGS],
    # Configure minimal required settings, use `Validator()`
    # validators=[],
    ENVVAR_PREFIX_FOR_DYNACONF="APP_SPARK_API",
    ENVVAR_FOR_DYNACONF="APP_SPARK_API_SETTINGS",
)

# Django 项目使用的 SECRET_KEY，默认值不安全，建议使用真实生成的随机 secret 重载
# 示例命令： python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY = settings.get(
    "SECRET_KEY",
    "django-insecure-^_*&rfc*!0j9hbv72brmurr@8t^gd)$zq@19jb0xze-)7g^!0i",
)
DEBUG = settings.get("DEBUG", False)

# 允许通过什么域名访问服务，详见：https://docs.djangoproject.com/zh-hans/6.1/ref/settings/#allowed-hosts
ALLOWED_HOSTS = settings.get("ALLOWED_HOSTS", ["*"])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # bkpaas_auth is used as the authentication lib for the project, based on contrib.auth but
    # with not real database users.
    "bkpaas_auth",
    "app_spark_api.infras.accounts.apps.AccountsConfig",
]


# Required config for using `bkpaas-auth` lib
AUTH_USER_MODEL = "bkpaas_auth.User"
AUTHENTICATION_BACKENDS = [
    "bkpaas_auth.backends.UniversalAuthBackend",
    "bkpaas_auth.backends.APIGatewayAuthBackend",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "bkpaas_auth.middlewares.CookieLoginMiddleware",
    "bkpaas_auth.middlewares.UserTimezoneMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app_spark_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(__file__).resolve().parent.parent / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "app_spark_api.wsgi.application"
ASGI_APPLICATION = "app_spark_api.asgi.application"

# ------------------------
# Django 基础配置（自定义）
# ------------------------

DATABASES = {}

# 当未配置 default 数据库时不再强制报错，以允许 `manage.py --help`、`django-admin check`
# 等不需要数据库的运维命令正常执行。数据库仍是正式运行时的必选项。
if default_db_conf := get_database_conf(settings):
    DATABASES["default"] = default_db_conf

# == 缓存相关配置项
# DEFAULT_CACHE_CONFIG 优先级最高，若无该配置则检查是否配置 Redis，若存在则作为缓存, 否则使用临时文件作为缓存(仅适用于本地开发)
# WARNING: 生产环境请配置远程服务缓存, 如 RedisCache, DatabaseCache 等, 以保证多副本多 worker 时, 缓存数据一致, 否则可能无法正常工作
DEFAULT_CACHE_CONFIG = settings.get("DEFAULT_CACHE_CONFIG")
if DEFAULT_CACHE_CONFIG:
    CACHES = {"default": DEFAULT_CACHE_CONFIG}
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": "/tmp/django_cache",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators
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
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = settings.get("LANGUAGE_CODE", "zh-hans")
LANGUAGES = tuple(
    settings.get(
        "LANGUAGES",
        (
            ("zh-hans", "简体中文"),
            ("en", "English"),
        ),
    )
)
TIME_ZONE = settings.get("TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = (str(BASE_DIR / "locale"),)

# 国际化 cookie 信息必须跟整个蓝鲸体系保存一致
LANGUAGE_COOKIE_NAME = settings.get("LANGUAGE_COOKIE_NAME", "blueking_language")
LANGUAGE_COOKIE_PATH = settings.get("LANGUAGE_COOKIE_PATH", "/")
LANGUAGE_COOKIE_DOMAIN = settings.get("LANGUAGE_COOKIE_DOMAIN", settings.get("BK_COOKIE_DOMAIN"))

# 是否启用多租户模式，本配置项仅支持在初次部署时配置，部署后不支持动态调整
ENABLE_MULTI_TENANT_MODE = settings.get("ENABLE_MULTI_TENANT_MODE", False)

# --------
# 各系统地址相关配置
# --------

# 统一登录页面地址，用于模板渲染，必填
LOGIN_FULL = settings.get("LOGIN_FULL", "")

# --------
# 用户鉴权模块 bkpaas_auth SDK 相关配置
# --------

# 是否启用多租户模式, 需要和 ENABLE_MULTI_TENANT_MODE 保持一致
BKAUTH_ENABLE_MULTI_TENANT_MODE = ENABLE_MULTI_TENANT_MODE

BKAUTH_BACKEND_TYPE = settings.get("BKAUTH_BACKEND_TYPE", "bk_token")
BKAUTH_TOKEN_APP_CODE = settings.get("BKAUTH_TOKEN_APP_CODE", "")
BKAUTH_TOKEN_SECRET_KEY = settings.get("BKAUTH_TOKEN_SECRET_KEY", "")

# 如果当前环境没有 bk-login 网关，则设置 BKAUTH_USER_INFO_APIGW_URL 为空字符串, bkpaas_auth 将使用 BKAUTH_USER_COOKIE_VERIFY_URL
# 如果设置了有效的 BKAUTH_USER_INFO_APIGW_URL, BKAUTH_USER_COOKIE_VERIFY_URL 配置将被忽略, 使用网关进行用户身份校验
# 多租户模式下(BKAUTH_ENABLE_MULTI_TENANT_MODE=True)必须设置有效的 BKAUTH_USER_INFO_APIGW_URL, 否则无法使用租户功能
BKAUTH_BK_LOGIN_APIGW_STAGE = settings.get("BKAUTH_BK_LOGIN_APIGW_STAGE", "prod")
BKAUTH_USER_INFO_APIGW_URL = settings.get("BKAUTH_USER_INFO_APIGW_URL", "")
BKAUTH_USER_COOKIE_VERIFY_URL = settings.get("BKAUTH_USER_COOKIE_VERIFY_URL", "")

BKAUTH_TOKEN_USER_INFO_ENDPOINT = settings.get("BKAUTH_TOKEN_USER_INFO_ENDPOINT", "")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.2/howto/static-files/
STATIC_ROOT = str(BASE_DIR / "public" / "static")
STATIC_URL = settings.get("STATIC_URL", "/static/")
