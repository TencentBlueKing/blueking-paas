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

from textwrap import dedent

import pytest
import yaml
from blue_krill.web.std_error import APIError
from django.core.files.base import ContentFile
from rest_framework.serializers import ValidationError

from paasng.platform.engine import serializers as slzs
from paasng.platform.engine.models.config_var import ConfigVar


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("environment_name", "bk_env"),
    [("stag", "bk_stag_env"), ("prod", "bk_prod_env"), ("_global_", None)],
    indirect=["bk_env"],
)
class TestConfigVar:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (dict(key="FOO", value="bar", is_sensitive=False, description="baz"), {}),
            pytest.param(
                dict(key="BKPAAS_FOO", value="bar", description="baz"),
                {},
                marks=pytest.mark.xfail(raises=ValidationError),
            ),
        ],
    )
    def test_input(self, bk_module, environment_name, bk_env, data, expected):
        slz = slzs.ConfigVarSLZ(data=dict(environment_name=environment_name, **data), context={"module": bk_module})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data == dict(
            environment=bk_env,
            module=bk_module,
            tenant_id=bk_module.tenant_id,
            environment_id=getattr(bk_env, "pk", -1),
            is_global=bk_env is None,
            **data,
        )

    @pytest.mark.parametrize(
        "data",
        [dict(key="FOO", value="bar", is_sensitive=False, description="baz")],
    )
    def test_output(self, bk_module, environment_name, bk_env, data):
        slz = slzs.ConfigVarSLZ(dict(module=bk_module, environment=bk_env, **data))
        assert slz.data == dict(environment_name=environment_name, module=bk_module.pk, **data)


@pytest.mark.django_db
class TestConfigVarImportSLZ:
    @pytest.fixture()
    def expected(self, request):
        for var in request.param:
            var["environment"] = request.getfixturevalue(var["environment"]) if var["environment"] else None
            var["module"] = request.getfixturevalue(var["module"])
        return [ConfigVar(**item) for item in request.param]

    @pytest.mark.parametrize(
        ("file_content", "expected"),
        [
            (dict(env_variables=[]), []),
            (
                dict(env_variables=[dict(key="FOO", value="bar", environment_name="stag", description="baz")]),
                [dict(key="FOO", value="bar", description="baz", environment="bk_stag_env", module="bk_module")],
            ),
            (
                dict(
                    env_variables=[
                        dict(key="FOO", value="bar", environment_name="prod", description="baz"),
                        dict(key="FOO", value="bar", environment_name="_global_", description="baz"),
                    ]
                ),
                [
                    dict(key="FOO", value="bar", description="baz", environment="bk_prod_env", module="bk_module"),
                    dict(
                        key="FOO", value="bar", description="baz", environment=None, module="bk_module", is_global=True
                    ),
                ],
            ),
            pytest.param(
                dict(env_variables=[dict(key="FOO", value="bar", environment_name="???", description="baz")]),
                [],
                marks=[pytest.mark.xfail(raises=ValidationError)],
            ),
        ],
        indirect=["expected"],
    )
    def test_normal(self, bk_module, file_content, expected):
        file = ContentFile(yaml.dump(file_content), "dummy")
        slz = slzs.ConfigVarImportSLZ(data=dict(file=file), context={"module": bk_module})
        slz.is_valid(raise_exception=True)
        assert (
            slzs.ConfigVarSLZ(slz.validated_data["env_variables"], many=True).data
            == slzs.ConfigVarSLZ(expected, many=True).data
        )

    def test_with_conment(self, bk_module, bk_stag_env, bk_prod_env):
        file = ContentFile(
            dedent(
                """
        # 环境变量文件字段说明：
        #   - key: 变量名称，仅支持大写字母、数字、下划线
        #   - value: 变量值
        #   - description: 描述文字
        #   - environment_name: 生效环境
        #     - 可选值:
        #       - stag: 预发布环境
        #       - prod: 生产环境
        #       - _global_: 所有环境
        env_variables:
            -   key: "FOO"
                value: "bar"
                description: ""
                environment_name: "stag"
            -   key: "FOO"
                value: "bar"
                description: null
                environment_name: "prod"
            -   key: "FOO"
                value: "bar"
                environment_name: "_global_"
        """
            ),
            "dummy",
        )
        expected = [
            ConfigVar(key="FOO", value="bar", description="", environment=bk_stag_env, module=bk_module),
            ConfigVar(key="FOO", value="bar", description=None, environment=bk_prod_env, module=bk_module),
            ConfigVar(key="FOO", value="bar", description="", environment_id=-1, is_global=True, module=bk_module),
        ]
        slz = slzs.ConfigVarImportSLZ(data=dict(file=file), context={"module": bk_module})
        slz.is_valid(raise_exception=True)
        assert (
            slzs.ConfigVarSLZ(slz.validated_data["env_variables"], many=True).data
            == slzs.ConfigVarSLZ(expected, many=True).data
        )

    def test_error(self, bk_module, bk_stag_env, bk_prod_env):
        file = ContentFile(
            dedent(
                """
            -   key: "FOO"
                value: "bar"
                description: ""
                environment_name: "stag"
            -   key: "FOO"
                value: "bar"
                description: null
                environment_name: "prod"
            -   key: "FOO"
                value: "bar"
                environment_name: "_global_"
        """
            ),
            "dummy",
        )
        slz = slzs.ConfigVarImportSLZ(data=dict(file=file), context={"module": bk_module})
        with pytest.raises(APIError):
            slz.is_valid(raise_exception=True)

    def test_key_error(self, bk_module, bk_stag_env, bk_prod_env):
        """变量 key 不能包含小写字母"""
        file = ContentFile(
            dedent(
                """
        env_variables:
            -   key: "foo"
                value: "bar"
                description: ""
                environment_name: "stag"
        """
            ),
            "dummy",
        )
        slz = slzs.ConfigVarImportSLZ(data=dict(file=file), context={"module": bk_module})
        with pytest.raises(ValidationError):
            slz.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestConfigVarBaseInputSLZ:
    @pytest.fixture()
    def expected(self, request):
        request.param["environment"] = (
            request.getfixturevalue(request.param["environment"]) if request.param["environment"] else None
        )
        request.param["module"] = request.getfixturevalue(request.param["module"])
        return ConfigVar(**request.param)

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                dict(key="FOO", value="bar", environment_name="stag", description="baz"),
                dict(key="FOO", value="bar", description="baz", environment="bk_stag_env", module="bk_module"),
            )
        ],
        indirect=["expected"],
    )
    def test_normal(self, bk_module, data, expected):
        slz = slzs.ConfigVarBaseInputSLZ(data=data, context={"module": bk_module})
        slz.is_valid(raise_exception=True)
        assert slzs.ConfigVarSLZ(slz.validated_data).data == slzs.ConfigVarSLZ(expected).data
