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

import pytest
from rest_framework import serializers

from paasng.platform.agent_sandbox.serializers import SandboxEnvField


class DummyEnvSerializer(serializers.Serializer):
    env = SandboxEnvField(required=False, default=dict)


def test_env_must_be_object():
    slz = DummyEnvSerializer(data={"env": "not-object"})

    assert not slz.is_valid()
    assert str(slz.errors["env"][0]) == "env must be an object"


@pytest.mark.parametrize(
    "env_value",
    [{1: "one"}, {"FOO": 1}, {"FOO": "BAR", "COUNT": 1}],
)
def test_env_must_be_string_mapping(env_value):
    slz = DummyEnvSerializer(data={"env": env_value})

    assert not slz.is_valid()
    assert str(slz.errors["env"][0]) == "env must be an object of string key-value pairs"


def test_env_accepts_string_mapping():
    env = {"FOO": "BAR", "EMPTY": ""}
    slz = DummyEnvSerializer(data={"env": env})

    slz.is_valid(raise_exception=True)
    assert slz.validated_data["env"] == env
