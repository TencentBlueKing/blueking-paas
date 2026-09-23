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

from unittest.mock import MagicMock

from paasng.accessories.servicehub.mysql_plan_migration import align_binding


def _attachment(*, plan_id: str, service_instance_id: str | None):
    attachment = MagicMock()
    attachment.plan_id = plan_id
    attachment.service_instance_id = service_instance_id
    return attachment


def test_unprovisioned_binding_switches_plan_immediately():
    """还没开通的环境直接改绑定。"""
    attachment = _attachment(plan_id="source", service_instance_id=None)

    message, updated = align_binding(attachment, "target", None, "app/default/prod")

    assert updated is True
    assert attachment.plan_id == "target"
    attachment.save.assert_called_once_with(update_fields=["plan_id"])
    assert "尚未开通" in message


def test_provisioned_binding_waits_until_instance_plan_matches():
    """实例还在源 plan 时不改绑定。"""
    attachment = _attachment(plan_id="source", service_instance_id="instance-1")

    message, updated = align_binding(attachment, "target", "source", "app/default/stag")

    assert updated is False
    assert attachment.plan_id == "source"
    attachment.save.assert_not_called()
    assert "migrate_plan switch" in message


def test_provisioned_binding_updates_after_instance_is_on_target_plan():
    """实例已经是目标 plan 时才把绑定对齐。"""
    attachment = _attachment(plan_id="source", service_instance_id="instance-1")

    message, updated = align_binding(attachment, "target-id", "target-id", "app/default/stag")

    assert updated is True
    assert attachment.plan_id == "target-id"
    assert "重新部署" in message
