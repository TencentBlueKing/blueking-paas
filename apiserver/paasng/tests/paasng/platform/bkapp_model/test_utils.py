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

from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay
from paasng.platform.bkapp_model.utils import MergeStrategy, merge_env_vars, override_env_vars_overlay


@pytest.mark.parametrize(
    ("x", "y", "strategy", "z"),
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
def test_merge_env_vars(x, y, strategy, z):
    assert merge_env_vars(x, y, strategy) == z


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        ([], [], []),
        (
            [],
            [EnvVarOverlay(name="a", value="a", envName="stag")],
            [],
        ),
        (
            [EnvVarOverlay(name="a", value="b", envName="stag")],
            [EnvVarOverlay(name="a", value="c", envName="stag")],
            [EnvVarOverlay(name="a", value="c", envName="stag")],
        ),
        (
            [EnvVarOverlay(name="a", value="b", envName="stag")],
            [EnvVarOverlay(name="a", value="c", envName="prod")],
            [EnvVarOverlay(name="a", value="b", envName="stag")],
        ),
        (
            [EnvVarOverlay(name="a", value="b", envName="stag")],
            [
                EnvVarOverlay(name="a", value="d", envName="prod"),
                EnvVarOverlay(name="a", value="dddd", envName="stag"),
            ],
            [
                EnvVarOverlay(name="a", value="dddd", envName="stag"),
            ],
        ),
        (
            [
                EnvVarOverlay(name="a", value="b", envName="stag"),
                EnvVarOverlay(name="a", value="cccc", envName="prod"),
            ],
            [
                EnvVarOverlay(name="a", value="d", envName="prod"),
            ],
            [
                EnvVarOverlay(name="a", value="b", envName="stag"),
                EnvVarOverlay(name="a", value="d", envName="prod"),
            ],
        ),
        (
            [
                EnvVarOverlay(name="a", value="b", envName="stag"),
                EnvVarOverlay(name="a", value="cccc", envName="prod"),
            ],
            [
                EnvVarOverlay(name="a", value="d", envName="prod"),
                EnvVarOverlay(name="b", value="qqq", envName="stag"),
            ],
            [
                EnvVarOverlay(name="a", value="b", envName="stag"),
                EnvVarOverlay(name="a", value="d", envName="prod"),
            ],
        ),
    ],
)
def test_override_env_vars_overlay(x, y, expected):
    assert override_env_vars_overlay(x, y) == expected
