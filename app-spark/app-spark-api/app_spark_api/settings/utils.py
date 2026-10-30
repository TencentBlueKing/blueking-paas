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
from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import quote

if TYPE_CHECKING:
    from dynaconf.base import LazySettings


def get_database_conf(settings: LazySettings) -> Optional[Dict]:
    """Get a database config dict."""

    database_name = settings.get("DATABASE_NAME")
    if database_name:
        database_user = settings.get("DATABASE_USER", None)
        database_password = settings.get("DATABASE_PASSWORD", None)
        database_host = settings.get("DATABASE_HOST", None)
        database_port = settings.get("DATABASE_PORT", None)
        database_options = settings.get("DATABASE_OPTIONS", {})

        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": database_name,
            "USER": database_user,
            "PASSWORD": database_password,
            "HOST": database_host,
            "PORT": database_port,
            "OPTIONS": database_options,
        }
    return None


def build_rabbitmq_broker_url(settings: LazySettings) -> str:
    """Build the AMQP URL from the five broker settings."""

    # 没写的项用占位，跟其他 settings.get 一样。不在这里连队列。
    host = settings.get("RABBITMQ_HOST", "rabbitmq.example.com")
    port = settings.get("RABBITMQ_PORT", 5672)
    user = quote(str(settings.get("RABBITMQ_USER", "app-spark")), safe="")
    password = quote(str(settings.get("RABBITMQ_PASSWORD", "test-rabbitmq-password")), safe="")
    vhost = quote(str(settings.get("RABBITMQ_VHOST", "app-spark")), safe="")
    return f"amqp://{user}:{password}@{host}:{port}/{vhost}"
