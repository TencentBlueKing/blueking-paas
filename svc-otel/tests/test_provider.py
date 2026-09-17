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

from unittest.mock import MagicMock, patch

import pytest
from svc_otel.vendor.models import ApmData
from svc_otel.vendor.provider import Provider

pytestmark = pytest.mark.django_db


def test_reuse_local_apm_data_without_remote_request():
    existing = ApmData.objects.create(
        bk_app_code="demo-app",
        env="stag",
        app_name="bkapp_demo0us0app_stag_legacy",
        data_token="local-token",
    )

    with patch("svc_otel.vendor.provider.make_bk_monitor_client") as make_client:
        result = Provider()._apply_data_token("demo-app", "stag", "bkpaas__demo", "default")

    assert result.pk == existing.pk
    assert result.app_name == "bkapp_demo0us0app_stag_legacy"
    assert result.data_token == "local-token"
    make_client.assert_not_called()


def test_get_or_create_remote_apm_once_and_persist_locally():
    client = MagicMock()
    client.get_or_create_apm.return_value = "remote-token"

    with patch("svc_otel.vendor.provider.make_bk_monitor_client", return_value=client) as make_client:
        first = Provider()._apply_data_token("demo-app", "prod", "bkpaas__demo", "default")
        second = Provider()._apply_data_token("demo-app", "prod", "bkpaas__demo", "default")

    assert first.pk == second.pk
    assert first.app_name == "bkapp_demo0us0app_prod"
    assert first.data_token == "remote-token"
    assert ApmData.objects.filter(bk_app_code="demo-app", env="prod").count() == 1
    make_client.assert_called_once_with("default")
    client.get_or_create_apm.assert_called_once_with("bkapp_demo0us0app_prod", "bkpaas__demo")
