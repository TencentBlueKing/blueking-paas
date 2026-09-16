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

from http import HTTPStatus
from unittest import mock

import pytest

from paasng.infras.iam import utils
from paasng.infras.iam.constants import BK_LOG_SYSTEM_ID, BK_MONITOR_SYSTEM_ID
from paasng.infras.iam.exceptions import (
    BKIAMApiHTTPError,
    BKIAMCapabilityNotSupportedError,
)
from paasng.infras.iam.v4.management import BKIAMV4ManagementBackend
from paasng.infras.iam.v4.spaces import SPACE_OPERATOR_ROLE_ID


@pytest.fixture()
def backend(settings) -> BKIAMV4ManagementBackend:
    settings.IAM_PAAS_V3_SYSTEM_ID = "bk_paas3"
    return BKIAMV4ManagementBackend("tenant-foo", operator="admin")


class TestCreateManagementSpace:
    def test_writes_three_systems_and_operator(self, backend):
        """创建时一次性写入三个系统的权限范围，且写操作携带操作人"""
        backend.call = mock.Mock(return_value={"data": {"id": 42}})  # type: ignore

        assert backend.create_management_space("app-code", "App", "someone", bk_space_id="-100") == 42

        backend.call.assert_called_once()
        kwargs = backend.call.call_args.kwargs
        assert kwargs["for_write"] is True
        assert kwargs["path_params"] == {"system_id": "bk_paas3"}
        assert kwargs["data"]["managers"] == ["someone"]
        assert kwargs["data"]["subject_scope"] == {"users": ["*"]}
        assert kwargs["data"]["name"] == utils.gen_grade_manager_name("app-code")

        scopes = kwargs["data"]["permission_scope"]
        systems = {item["system"] for item in scopes}
        assert systems == {"bk_paas3", BK_MONITOR_SYSTEM_ID, BK_LOG_SYSTEM_ID}
        observability = [item for item in scopes if item["system"] in {BK_MONITOR_SYSTEM_ID, BK_LOG_SYSTEM_ID}]
        assert {item["id"] for item in observability} == {SPACE_OPERATOR_ROLE_ID}

    def test_without_bk_space_id_only_writes_paas(self, backend):
        backend.call = mock.Mock(return_value={"data": {"id": 1}})  # type: ignore

        backend.create_management_space("app-code", "App", "someone")

        systems = {item["system"] for item in backend.call.call_args.kwargs["data"]["permission_scope"]}
        assert systems == {"bk_paas3"}

    def test_conflict_reuses_existing_space_id(self, backend):
        """同名空间已存在时回查并复用 ID，不抛未处理异常"""
        backend.call = mock.Mock(  # type: ignore
            side_effect=BKIAMApiHTTPError(
                "space already exists", status_code=HTTPStatus.CONFLICT, request_id="req-409"
            )
        )
        existing_name = utils.gen_grade_manager_name("app-code")
        backend.paginate = mock.Mock(  # type: ignore
            return_value=iter([{"id": 7, "name": existing_name}, {"id": 8, "name": "other"}])
        )

        assert backend.create_management_space("app-code", "App", "someone") == 7


class TestCapabilityNotSupported:
    def test_update_management_space_scopes(self, backend):
        """V4 下不需要更新管理空间，创建时已写齐三系统范围"""
        with pytest.raises(BKIAMCapabilityNotSupportedError) as exc_info:
            backend.update_management_space_scopes(1, "app-code", "App", "-1")

        assert exc_info.value.capability == "更新管理空间的授权范围"
        assert "V4 暂未提供该能力" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("method", "args", "capability"),
        [
            ("delete_management_space", (1,), "删除管理空间"),
            ("add_management_space_members", (1, ["user-0"]), "添加管理空间成员"),
            ("delete_management_space_members", (1, ["user-0"]), "删除管理空间成员"),
        ],
    )
    def test_missing_space_member_apis(self, backend, method, args, capability):
        """V4 暂缺能力必须明确抛异常，不能静默返回成功，也不能绕行"""
        with pytest.raises(BKIAMCapabilityNotSupportedError) as exc_info:
            getattr(backend, method)(*args)

        assert exc_info.value.capability == capability
        assert "V4 暂未提供该能力" in str(exc_info.value)


class TestResolveV4BkSpaceId:
    def test_v3_skips_monitor_space(self, settings):
        from paasng.platform.applications.helpers import _resolve_v4_bk_space_id

        settings.BK_IAM_VERSION = "v3"
        assert _resolve_v4_bk_space_id(mock.Mock(code="app-code")) is None

    def test_v4_returns_monitor_space_id(self, settings):
        from paasng.platform.applications.helpers import _resolve_v4_bk_space_id

        settings.BK_IAM_VERSION = "v4"
        space = mock.Mock(iam_resource_id="-100")
        with mock.patch(
            "paasng.platform.applications.helpers.get_or_create_bk_monitor_space",
            return_value=(space, True),
        ) as mocked:
            assert _resolve_v4_bk_space_id(mock.Mock(code="app-code")) == "-100"
            mocked.assert_called_once()
