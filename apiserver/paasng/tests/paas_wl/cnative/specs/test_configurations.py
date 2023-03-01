# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import pytest

from paas_wl.cnative.specs.configurations import MergeStrategy, generate_builtin_configurations, merge_envvars
from paas_wl.cnative.specs.v1alpha1.bk_app import EnvVar

pytestmark = pytest.mark.django_db(databases=["default"])


def test_generate_builtin_configurations(bk_stag_env, bk_prod_env):
    configurations = generate_builtin_configurations(bk_stag_env)
    assert {"BKPAAS_APP_ID", "BKPAAS_APP_SECRET", "BK_LOGIN_URL"} - {item.name for item in configurations} == set()


@pytest.mark.parametrize(
    "x, y, strategy, z",
    [
        ([], [], MergeStrategy.OVERRIDE, []),
        ([], [EnvVar(name="a", value="a")], MergeStrategy.OVERRIDE, [EnvVar(name="a", value="a")]),
        ([EnvVar(name="a", value="a")], [], MergeStrategy.OVERRIDE, [EnvVar(name="a", value="a")]),
        (
            [EnvVar(name="a", value="a")],
            [EnvVar(name="a", value="A")],
            MergeStrategy.OVERRIDE,
            [EnvVar(name="a", value="A")],
        ),
        (
            [EnvVar(name="a", value="a")],
            [EnvVar(name="a", value="A")],
            MergeStrategy.IGNORE,
            [EnvVar(name="a", value="a")],
        ),
        # override 在原来的位置修改, 然后再 append
        (
            [EnvVar(name="a", value="a"), EnvVar(name="b", value="b")],
            [EnvVar(name="B", value="B"), EnvVar(name="a", value="A")],
            MergeStrategy.OVERRIDE,
            [EnvVar(name="a", value="A"), EnvVar(name="b", value="b"), EnvVar(name="B", value="B")],
        ),
    ],
)
def test_merge_envvars(x, y, strategy, z):
    assert merge_envvars(x, y, strategy) == z
