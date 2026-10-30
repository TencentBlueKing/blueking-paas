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

"""Broker settings are checked without opening a connection."""

from app_spark_api.settings.utils import build_rabbitmq_broker_url


def test_build_rabbitmq_broker_url_encodes_the_password_and_vhost():
    settings = {
        "RABBITMQ_HOST": "rabbitmq.example.com",
        "RABBITMQ_PORT": 5672,
        "RABBITMQ_USER": "app-spark",
        "RABBITMQ_PASSWORD": "s3cret-broker-password",
        "RABBITMQ_VHOST": "app spark/vhost",
    }

    assert build_rabbitmq_broker_url(settings) == (
        "amqp://app-spark:s3cret-broker-password@rabbitmq.example.com:5672/app%20spark%2Fvhost"
    )


def test_build_rabbitmq_broker_url_uses_placeholders_when_unset():
    assert build_rabbitmq_broker_url({}) == (
        "amqp://app-spark:test-rabbitmq-password@rabbitmq.example.com:5672/app-spark"
    )
