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
from unittest.mock import MagicMock, patch

import pytest
from django.core.management.base import CommandError
from vendor.constants import DEFAULT_STREAM_PORT
from vendor.helper import InstanceHelper
from vendor.management.commands.sync_stream_port import Command as SyncStreamPortCommand
from vendor.provider import Provider

from .conftest import make_cluster

CREDENTIALS = {"host": "127.0.0.1", "port": 5672, "user": "user", "password": "secret", "vhost": "vhost"}


def test_new_instance_gets_plan_stream_port():
    """方案开启 stream 时，新实例凭证带上方案配置的端口。

    凭证里的 key 必须是 stream_port，写成 RABBITMQ_STREAM_PORT 会被平台加成双前缀。
    """
    bill = MagicMock()
    bill.uuid.hex = "billuuidhex"

    # 插件与 RabbitMQ 的交互不在本用例关注范围内
    with patch("vendor.provider.Client.from_cluster"), patch("vendor.provider.PROVIDER_PLUGINS", []):
        provider = Provider(enable_stream=True, stream_port=6552)
        instance_data = provider.create_instance("app", bill, {}, make_cluster())

    assert instance_data.credentials["stream_port"] == 6552


def test_get_credentials_tolerates_stream_port():
    """凭证多出 stream_port 后，巡检任务取凭证不能报错。"""
    instance = MagicMock()
    instance.credentials = json.dumps({**CREDENTIALS, "stream_port": DEFAULT_STREAM_PORT})

    assert InstanceHelper(instance).get_credentials().vhost == "vhost"


def test_sync_stream_port_backfills_instance():
    """指定方案后，存量实例凭证被回填 stream_port。"""
    plan = MagicMock()
    plan.name = "default"
    plan.get_config.return_value = {"enable_stream": True, "stream_port": 6552}

    instance = MagicMock()
    instance.uuid = "ins-1"
    instance.get_credentials.return_value = dict(CREDENTIALS)

    with (
        patch("vendor.management.commands.sync_stream_port.Plan") as mock_plan,
        patch("vendor.management.commands.sync_stream_port.ServiceInstance") as mock_si,
    ):
        mock_plan.objects.get.return_value = plan
        mock_si.objects.filter.return_value = [instance]
        SyncStreamPortCommand().handle(plan_id="plan-uuid", dry_run=False)

    instance.save.assert_called_once()
    assert json.loads(instance.credentials)["stream_port"] == 6552


def test_sync_stream_port_dry_run_does_not_save():
    """--dry-run 只打印范围，不写库。"""
    plan = MagicMock()
    plan.name = "default"
    plan.get_config.return_value = {"enable_stream": True, "stream_port": DEFAULT_STREAM_PORT}

    instance = MagicMock()
    instance.uuid = "ins-1"
    instance.get_credentials.return_value = dict(CREDENTIALS)

    with (
        patch("vendor.management.commands.sync_stream_port.Plan") as mock_plan,
        patch("vendor.management.commands.sync_stream_port.ServiceInstance") as mock_si,
    ):
        mock_plan.objects.get.return_value = plan
        mock_si.objects.filter.return_value = [instance]
        SyncStreamPortCommand().handle(plan_id="plan-uuid", dry_run=True)

    instance.save.assert_not_called()


def test_sync_stream_port_requires_enable_stream():
    """未开启 stream 的方案不允许回填，避免误写入环境变量。"""
    plan = MagicMock()
    plan.name = "default"
    plan.get_config.return_value = {"enable_stream": False}

    with patch("vendor.management.commands.sync_stream_port.Plan") as mock_plan:
        mock_plan.objects.get.return_value = plan
        with pytest.raises(CommandError, match="enable_stream"):
            SyncStreamPortCommand().handle(plan_id="plan-uuid", dry_run=False)
