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

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / ...
BASE_DIR = Path(__file__).parents[2].absolute()

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
    "svc_redis.vendor",
    "svc_redis.cluster",
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

ROOT_URLCONF = "svc_redis.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "svc_redis/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "svc_redis.middleware.context_processors",
            ],
        },
    },
]

WSGI_APPLICATION = "svc_redis.wsgi.application"

# Database

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Internationalization

LANGUAGE_CODE = "zh-cn"

LANGUAGES = [("zh-cn", "简体中文"), ("en", "English")]

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGGING_LEVEL = "DEBUG"

BKKRILL_ENCRYPT_SECRET_KEY = "Q3NyY0V3cFpTUlVNbHp3RUZMYWtXaEdOdXp3eWZNSkc=".encode()

# 增强服务供应商类
PAAS_SERVICE_PROVIDER_CLS = "svc_redis.vendor.provider.Provider"
# 增强服务实例信息渲染函数
PAAS_SERVICE_SVC_INSTANCE_RENDER_FUNC = "svc_redis.vendor.render.render_instance_data"

PAAS_SERVICE_JWT_CLIENTS = [
    {
        "iss": "paas-v3",
        "key": "D/AcILSskkPrwoHfuLuE9+DnEGnxVX9BbQKGjoeCpgg=",
        "algorithm": "HS256",
    },
]

# 是否开启管理端功能
ENABLE_ADMIN = False

# 选择加密数据库内容的算法，可选择：'SHANGMI' , 'CLASSIC'
BK_CRYPTO_TYPE = "CLASSIC"
ENCRYPT_CIPHER_TYPE = "FernetCipher"
