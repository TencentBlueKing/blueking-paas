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

from paasng.platform.agent_sandbox.e2b.constants import MAX_TEMPLATE_PREWARM_COUNT, MIN_TEMPLATE_MEMORY_MB
from paasng.platform.agent_sandbox.e2b.serializers import E2BBuiltinTemplateUpdateInputSLZ, E2BTemplateSpecInputSLZ


def _validate_env_vars(env_vars: dict) -> E2BTemplateSpecInputSLZ:
    slz = E2BTemplateSpecInputSLZ(data={"name": "n", "image": "img", "env_vars": env_vars})
    slz.is_valid()
    return slz


class TestTemplateSpecEnvVars:
    @pytest.mark.parametrize("name", ["FOO\n", "1FOO", "FOO-BAR", " FOO", ""])
    def test_invalid_name(self, name):
        slz = _validate_env_vars({name: "x"})
        assert "env_vars" in slz.errors

    def test_value_whitespace_preserved(self):
        env_vars = {"_FOO1": "  a b \n", "EMPTY": ""}
        slz = _validate_env_vars(env_vars)
        assert not slz.errors
        assert slz.validated_data["env_vars"] == env_vars


class TestBuiltinTemplateLimits:
    @pytest.mark.parametrize(
        ("field", "value", "valid"),
        [
            ("memory_mb", MIN_TEMPLATE_MEMORY_MB, True),
            ("memory_mb", MIN_TEMPLATE_MEMORY_MB - 1, False),
            ("prewarm_count", MAX_TEMPLATE_PREWARM_COUNT, True),
            ("prewarm_count", MAX_TEMPLATE_PREWARM_COUNT + 1, False),
        ],
    )
    def test_bounds(self, field, value, valid):
        slz = E2BBuiltinTemplateUpdateInputSLZ(data={"name": "n", "image": "img", field: value})
        assert slz.is_valid() is valid
