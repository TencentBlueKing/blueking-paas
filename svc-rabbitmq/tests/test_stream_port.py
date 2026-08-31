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

import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from paas_service.models import Plan
from vendor.constants import DEFAULT_STREAM_PORT
from vendor.helper import InstanceHelper
from vendor.provider import Provider

from .conftest import DEFAULT_INSTANCE_CREDENTIALS, make_cluster

STREAM_PORT = 6552


@pytest.fixture
def stream_plan(plan) -> Plan:
    """在默认方案上开启 stream，供回填命令复用。"""
    plan.config = json.dumps({"enable_stream": True, "stream_port": STREAM_PORT})
    plan.save(update_fields=["config", "updated"])
    return plan


def test_new_instance_gets_plan_stream_port():
    """方案开启 stream 时，新实例凭证带上方案配置的端口。

    凭证里的 key 必须是 stream_port，写成 RABBITMQ_STREAM_PORT 会被平台加成双前缀。
    """
    bill = SimpleNamespace(uuid=uuid4())

    # 插件与 RabbitMQ 的交互不在本用例关注范围内
    with patch("vendor.provider.Client.from_cluster"), patch("vendor.provider.PROVIDER_PLUGINS", []):
        provider = Provider(enable_stream=True, stream_port=STREAM_PORT)
        instance_data = provider.create_instance("app", bill, {}, make_cluster())

    assert instance_data.credentials["stream_port"] == STREAM_PORT


def test_get_credentials_tolerates_stream_port():
    """凭证多出 stream_port 后，巡检任务取凭证不能报错。"""
    instance = SimpleNamespace(
        credentials=json.dumps({**DEFAULT_INSTANCE_CREDENTIALS, "stream_port": DEFAULT_STREAM_PORT})
    )

    assert InstanceHelper(instance).get_credentials().vhost == "vhost"


@pytest.mark.django_db
def test_sync_stream_port_backfills_instance(stream_plan, instance):
    """指定方案后，存量实例凭证被回填 stream_port。"""
    call_command("sync_stream_port", plan_id=str(stream_plan.pk))

    instance.refresh_from_db()
    assert instance.get_credentials()["stream_port"] == STREAM_PORT


@pytest.mark.django_db
def test_sync_stream_port_dry_run_does_not_save(stream_plan, instance):
    """--dry-run 只打印范围，不写库。"""
    call_command("sync_stream_port", plan_id=str(stream_plan.pk), dry_run=True)

    instance.refresh_from_db()
    assert "stream_port" not in instance.get_credentials()


@pytest.mark.django_db
def test_sync_stream_port_requires_enable_stream(plan):
    """未开启 stream 的方案不允许回填，避免误写入环境变量。"""
    with pytest.raises(CommandError, match="enable_stream"):
        call_command("sync_stream_port", plan_id=str(plan.pk))
