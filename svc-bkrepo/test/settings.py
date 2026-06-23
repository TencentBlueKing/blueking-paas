# -*- coding: utf-8 -*-
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

"""测试专用 Django settings — 所有敏感值硬编码，不依赖环境变量"""

from pathlib import Path

BASE_DIR = Path(__file__).parents[2].absolute()

SECRET_KEY = "test-secret-key-not-for-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

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

ROOT_URLCONF = "svc_bk_repo.urls"

# Database

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Internationalization

LANGUAGE_CODE = "zh-cn"
LANGUAGES = [("zh-cn", "简体中文"), ("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

BKKRILL_ENCRYPT_SECRET_KEY = b"test-secret-not-for-production"

BKREPO_COLLECT_INTERVAL_MINUTES = 30

# 增强服务供应商类
PAAS_SERVICE_PROVIDER_CLS = "svc_bk_repo.vendor.provider.Provider"
# 增强服务方案配置 schema 类
PAAS_SERVICE_PLAN_SCHEMA_CLS = "svc_bk_repo.vendor.schema.PlanSchema"
# 增强服务实例信息渲染函数
PAAS_SERVICE_SVC_INSTANCE_RENDER_FUNC = "svc_bk_repo.vendor.render.render_instance_data"

PAAS_SERVICE_JWT_CLIENTS = [
    {
        "iss": "paas-v3",
        "key": "test-jwt-key-not-for-production",
        "algorithm": "HS256",
    },
]

BKREPO_DEFAULT_QUOTA = 2**30  # 1 GB

# bkrepo 扩容相关
EXTEND_CONFIG_MAX_SIZE_ALLOWED = 2**30 * 10  # 10 GB
EXTEND_CONFIG_EXTRA_SIZE_BYTES = 2**30  # 1 GB
BKREPO_AUTO_EXPAND_CHECK_INTERVAL_MINUTES = 20

BKAUTH_DEFAULT_PROVIDER_TYPE = "BK"
BKAUTH_BACKEND_TYPE = "bk_token"

AUTHENTICATION_BACKENDS = [
    "bkpaas_auth.backends.DjangoAuthUserCompatibleBackend",
]

BK_CRYPTO_TYPE = "CLASSIC"
ENCRYPT_CIPHER_TYPE = "FernetCipher"
