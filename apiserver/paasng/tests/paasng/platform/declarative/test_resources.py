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

from itertools import product
from typing import List
from unittest import mock

import pytest

from paasng.platform.declarative.application.resources import (
    ApplicationDesc,
    ApplicationDescDiffDog,
    DiffItem,
    ModuleDiffResult,
    ServiceSpec,
    mixed_service_mgr,
)
from paasng.platform.declarative.constants import DiffType

APP_DESC_INFO = dict(name_zh_cn="foo", name_en="foo", code="bar", region="baz")


pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def diff_result(param) -> ModuleDiffResult:
    return ModuleDiffResult(
        services=[
            DiffItem(
                resource=dict(name=service, display_name=service, shared_from=None, specs={}),
                diff_type=diff_type,
            )
            for services, diff_type in zip(param, [DiffType.DELETED, DiffType.NOT_MODIFIED, DiffType.ADDED])
            for service, diff_type in product(services, [diff_type])
        ]
    )


def make_modules(services: List[ServiceSpec], module_name: str = "default"):
    return {"modules": {module_name: {"name": module_name, "isDefault": True, "services": services}}}


class TestApplicationDescDiffDog:
    @pytest.mark.parametrize(
        ("service_names", "services", "expected"),
        [
            (
                (["a"], ["a"]),
                [ServiceSpec(name="a")],
                [[], ["a"], []],
            ),
            (
                (["a"], ["c", "a"]),
                [ServiceSpec(name="b"), ServiceSpec(name="c")],
                [["a"], ["c"], ["b"]],
            ),
            (
                (["b"], ["a"]),
                [ServiceSpec(name="a"), ServiceSpec(name="b"), ServiceSpec(name="c")],
                [[], ["a"], ["b", "c"]],
            ),
            (
                (["a", "c"], ["b", "c"]),
                [ServiceSpec(name="a"), ServiceSpec(name="d")],
                [["b", "c"], [], ["a", "d"]],
            ),
        ],
    )
    def test_diff_module(self, bk_app, bk_module, service_names, services, expected):
        def fake_list_binded(module):
            return [type("", (), dict(name=name)) for name in service_names[1]]

        with mock.patch.object(mixed_service_mgr, "list_binded") as list_binded:
            list_binded.side_effect = fake_list_binded

            desc = ApplicationDesc(**APP_DESC_INFO, **make_modules(services))
            assert ApplicationDescDiffDog(application=bk_app, desc=desc).diff() == {
                bk_module.name: diff_result(expected)
            }
