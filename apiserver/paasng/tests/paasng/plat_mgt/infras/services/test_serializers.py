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
from dataclasses import dataclass
from unittest import mock

import pytest
from rest_framework.exceptions import ValidationError

from paasng.accessories.servicehub.services import ServiceObj
from paasng.plat_mgt.infras.services.serializers.services import ServiceCreateSLZ


@dataclass
class StubServiceObj(ServiceObj):
    """用于测试的简单 ServiceObj 存根"""


def _make_stub_service(uuid: str, name: str) -> StubServiceObj:
    """创建一个用于测试的 ServiceObj 存根对象"""
    return StubServiceObj(uuid=uuid, name=name, logo="", is_visible=True)


class TestServiceCreateSLZValidateNameDuplication:
    """测试 ServiceCreateSLZ.validate_name 中禁止增强服务重名的逻辑"""

    @pytest.fixture()
    def current_service(self) -> StubServiceObj:
        """当前正在创建/更新的服务对象（放入 serializer context）"""
        return _make_stub_service(uuid="aaaa-1111", name="my-svc")

    @pytest.fixture()
    def existing_services(self) -> list:
        """模拟 mixed_service_mgr.list() 返回的已有服务列表"""
        return [
            _make_stub_service(uuid="bbbb-2222", name="mysql"),
            _make_stub_service(uuid="cccc-3333", name="redis"),
        ]

    @pytest.fixture()
    def _mock_list(self, existing_services):
        """Mock mixed_service_mgr.list() 返回预设的已有服务列表"""
        with mock.patch("paasng.plat_mgt.infras.services.serializers.services.mixed_service_mgr") as m:
            m.list.return_value = existing_services
            yield m

    def _run_validate_name(self, current_service: StubServiceObj, name: str) -> str:
        """构造 serializer 实例并调用 validate_name"""
        slz = ServiceCreateSLZ(context={"service": current_service})
        return slz.validate_name(name)

    @pytest.mark.usefixtures("_mock_list")
    def test_name_no_conflict(self, current_service):
        """名称与已有服务均不冲突时，校验通过并返回原名称"""
        result = self._run_validate_name(current_service, "new-svc")
        assert result == "new-svc"

    @pytest.mark.usefixtures("_mock_list")
    def test_name_conflicts_with_existing_service(self, current_service):
        """名称与另一个已有服务重名时，应抛出 ValidationError"""
        with pytest.raises(ValidationError, match="禁止存在相同的增强服务"):
            self._run_validate_name(current_service, "mysql")

    @pytest.mark.usefixtures("_mock_list")
    def test_update_allows_same_name_as_self(self, existing_services):
        """更新时，允许与自身重名（UUID 相同）"""
        # 使用已有服务列表中的第一个服务作为当前服务（模拟更新场景）
        self_service = existing_services[0]
        result = self._run_validate_name(self_service, self_service.name)
        assert result == self_service.name
