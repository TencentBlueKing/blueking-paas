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

import pytest

from paasng.platform.agent_sandbox.e2b.exceptions import E2BSandboxNotFound
from paasng.platform.agent_sandbox.models import E2BSandbox

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _new_sandbox(application, sandbox_id: str, **kwargs) -> E2BSandbox:
    return E2BSandbox.objects.create(
        sandbox_id=sandbox_id,
        application=application,
        cluster_name="cluster-a",
        tenant_id=application.tenant_id,
        **kwargs,
    )


class TestOwnedBy:
    def test_only_returns_own_sandboxes(self, bk_app, bk_app_full):
        """归属隔离：一个应用看不到另一个应用的实例。"""
        mine = _new_sandbox(bk_app, "sbx-mine")
        _new_sandbox(bk_app_full, "sbx-others")

        assert [s.sandbox_id for s in E2BSandbox.objects.owned_by(bk_app)] == [mine.sandbox_id]

    def test_returns_empty_without_sandboxes(self, bk_app, bk_app_full):
        _new_sandbox(bk_app_full, "sbx-others")

        assert not E2BSandbox.objects.owned_by(bk_app).exists()


class TestGetOwned:
    def test_returns_own_sandbox(self, bk_app):
        sandbox = _new_sandbox(bk_app, "sbx-mine")

        assert E2BSandbox.objects.get_owned(bk_app, "sbx-mine").pk == sandbox.pk

    def test_other_application_is_indistinguishable_from_missing(self, bk_app, bk_app_full):
        """他人的沙箱与不存在的沙箱必须报同一个错。

        若两者可区分，调用方返回的状态码就成了探测他人沙箱是否存在的信道。
        """
        _new_sandbox(bk_app_full, "sbx-others")

        with pytest.raises(E2BSandboxNotFound) as others:
            E2BSandbox.objects.get_owned(bk_app, "sbx-others")
        with pytest.raises(E2BSandboxNotFound) as unknown:
            E2BSandbox.objects.get_owned(bk_app, "sbx-never-existed")

        # 同一个异常类型，调用方无从区分「不属于你」与「不存在」，只能一律 404
        assert type(others.value) is type(unknown.value)
