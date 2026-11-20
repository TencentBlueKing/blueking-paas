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

from unittest.mock import patch

import pytest

from paasng.bk_plugins.bk_plugins.handlers import on_plugin_member_updated, on_pre_deployment
from tests.paasng.platform.engine.setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


@patch("paasng.bk_plugins.bk_plugins.handlers.safe_sync_apigw")
def test_on_pre_deployment(safe_sync_apigw, bk_plugin_app):
    deployment = create_fake_deployment(bk_plugin_app.default_module)
    on_pre_deployment(None, deployment=deployment)
    assert safe_sync_apigw.called is True


@patch("paasng.bk_plugins.bk_plugins.handlers.sync_plugin_apigw_maintainers")
def test_on_plugin_member_updated_for_plugin(mock_task, bk_plugin_app):
    # 插件应用成员变更应异步投递网关维护者同步任务
    on_plugin_member_updated(None, application=bk_plugin_app)
    mock_task.delay.assert_called_once_with(bk_plugin_app.code)


@patch("paasng.bk_plugins.bk_plugins.handlers.sync_plugin_apigw_maintainers")
def test_on_plugin_member_updated_for_non_plugin(mock_task, bk_app):
    # 非插件应用不应触发任何网关同步动作
    on_plugin_member_updated(None, application=bk_app)
    mock_task.delay.assert_not_called()


@patch("paasng.bk_plugins.bk_plugins.handlers.remove_plugin_apigw_maintainers")
@patch("paasng.bk_plugins.bk_plugins.handlers.sync_plugin_apigw_maintainers")
def test_on_plugin_member_updated_with_removed_usernames(mock_sync, mock_remove, bk_plugin_app):
    # 成员减少时，除全量同步外还需异步投递维护者移除任务
    on_plugin_member_updated(None, application=bk_plugin_app, removed_usernames=["leaver"])

    mock_sync.delay.assert_called_once_with(bk_plugin_app.code)
    mock_remove.delay.assert_called_once_with(bk_plugin_app.code, ["leaver"])


@patch("paasng.bk_plugins.bk_plugins.handlers.remove_plugin_apigw_maintainers")
@patch("paasng.bk_plugins.bk_plugins.handlers.sync_plugin_apigw_maintainers")
def test_on_plugin_member_updated_without_removed_usernames(mock_sync, mock_remove, bk_plugin_app):
    # 仅新增成员时不会传该参数，不应投递移除任务
    on_plugin_member_updated(None, application=bk_plugin_app)

    mock_sync.delay.assert_called_once_with(bk_plugin_app.code)
    mock_remove.delay.assert_not_called()


@patch("paasng.bk_plugins.bk_plugins.handlers.remove_plugin_apigw_maintainers")
def test_on_plugin_member_updated_non_plugin_with_removed_usernames(mock_remove, bk_app):
    # 非插件应用即使传了移除名单也不应投递任务
    on_plugin_member_updated(None, application=bk_app, removed_usernames=["leaver"])

    mock_remove.delay.assert_not_called()
