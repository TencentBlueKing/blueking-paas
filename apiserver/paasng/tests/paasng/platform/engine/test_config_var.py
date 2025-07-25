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

from string import ascii_uppercase
from textwrap import dedent
from typing import List

import pytest
from django.forms.models import model_to_dict
from django.utils.crypto import get_random_string
from rest_framework.exceptions import ValidationError

from paasng.platform.engine.configurations.env_var.listers import list_vars_user_configured
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import (
    CONFIG_VAR_INPUT_FIELDS,
    ENVIRONMENT_NAME_FOR_GLOBAL,
    ConfigVar,
)
from paasng.platform.engine.models.managers import ConfigVarManager, ExportedConfigVars, PlainConfigVar
from paasng.platform.engine.serializers import ConfigVarBaseInputSLZ, ConfigVarBatchInputSLZ, ConfigVarSLZ
from paasng.platform.modules.models import Module
from tests.utils.helpers import initialize_module

pytestmark = pytest.mark.django_db


class TestFilterByEnvironmentName:
    """Test cases for ConfigVar.objects.filter_by_environment_name"""

    @pytest.mark.parametrize(
        ("environment_name", "length", "keys"),
        [
            (ConfigVarEnvName.GLOBAL, 1, {"G1"}),
            (ConfigVarEnvName.STAG, 2, {"S1", "S2"}),
            (ConfigVarEnvName.PROD, 1, {"P1"}),
        ],
    )
    def test_global(self, bk_module, config_var_maker, environment_name: ConfigVarEnvName, length: int, keys: List):
        config_var_maker(key="S1", value="foo", environment_name="stag", module=bk_module)
        config_var_maker(key="S2", value="foo", environment_name="stag", module=bk_module)
        config_var_maker(key="P1", value="foo", environment_name="prod", module=bk_module)
        config_var_maker(key="G1", value="foo", environment_name=ENVIRONMENT_NAME_FOR_GLOBAL, module=bk_module)

        qs = ConfigVar.objects.filter(module=bk_module).filter_by_environment_name(environment_name)
        assert qs.count() == length
        assert {x.key for x in qs} == keys


@pytest.fixture()
def dest_module(bk_app):
    """Return another module if current application fixture"""
    module = Module.objects.create(
        application=bk_app, name="test", language="python", source_init_template="test", creator=bk_app.creator
    )
    initialize_module(module)
    return module


@pytest.fixture()
def dest_prod_env(dest_module):
    return dest_module.envs.get(environment="prod")


@pytest.fixture()
def random_config_var_maker():
    def maker(environment_name, **kwargs):
        kwargs.setdefault("key", get_random_string(length=12, allowed_chars=ascii_uppercase))
        kwargs.setdefault("value", get_random_string(12))
        kwargs.setdefault("description", get_random_string(12))
        kwargs["environment_name"] = environment_name
        return kwargs

    return maker


class TestConfigVarManager:
    @pytest.mark.parametrize(
        ("source_vars", "dest_vars", "expected_result", "expected_vars"),
        [
            (
                [
                    dict(
                        key="A",
                        value="2",
                    )
                ],
                [],
                (1, 0, 0),
                {"A": "2"},
            ),
            ([dict(key="A", value="2")], [dict(key="B", value="2")], (1, 0, 0), {"A": "2", "B": "2"}),
            (
                [dict(key="B", value="1")],
                [dict(key="B", value="2")],
                (0, 1, 0),
                {"B": "1"},
            ),
            (
                [dict(key="B", value="2", description="???")],
                [dict(key="B", value="2", description="!!!")],
                (0, 1, 0),
                {"B": "2"},
            ),
            (
                [dict(key="B", value="2", description="")],
                [dict(key="B", value="2", description="???")],
                (0, 1, 0),
                {"B": "2"},
            ),
            (
                [dict(key="B", value="2", description="aa")],
                [dict(key="B", value="2", description="aa")],
                (0, 0, 1),
                {"B": "2"},
            ),
            (
                [dict(key="A", value="2", description="A"), dict(key="B", value="d"), dict(key="C", value="d")],
                [dict(key="A", value="2", description="A"), dict(key="B", description="s")],
                (1, 1, 1),
                {"A": "2", "B": "d", "C": "d"},
            ),
        ],
    )
    def test_clone(
        self, config_var_maker, bk_module, dest_module, source_vars, dest_vars, expected_result, expected_vars
    ):
        for var in source_vars:
            config_var_maker(environment_name="prod", module=bk_module, **var)
        for var in dest_vars:
            config_var_maker(environment_name="prod", module=dest_module, **var)
        ret = ConfigVarManager().clone_vars(bk_module, dest_module)
        assert (ret.create_num, ret.overwrited_num, ret.ignore_num) == expected_result
        assert list_vars_user_configured(dest_module.get_envs("prod")).kv_map == expected_vars

    @pytest.mark.parametrize("maker_params", [{}, {"description": None}])
    def test_apply_vars_to_module(self, bk_module, random_config_var_maker, maker_params):
        serializer = ConfigVarBaseInputSLZ(
            data=[random_config_var_maker(environment_name="prod", **maker_params) for i in range(10)],
            context={"module": bk_module},
            many=True,
        )
        serializer.is_valid(raise_exception=True)
        config_vars = serializer.validated_data

        # 测试导入.
        ret = ConfigVarManager().apply_vars_to_module(bk_module, config_vars)
        assert (ret.create_num, ret.overwrited_num, ret.ignore_num) == (10, 0, 0)

        # 测试重复导入.
        ret = ConfigVarManager().apply_vars_to_module(bk_module, config_vars)
        assert (ret.create_num, ret.overwrited_num, ret.ignore_num) == (0, 0, 10)

        # 测试覆盖.
        another_list = [
            random_config_var_maker(
                environment_name="prod",
                key=var.key,
                value=get_random_string(length=len(var.value) - 1),
                **maker_params,
            )
            for var in config_vars
        ]
        serializer = ConfigVarBaseInputSLZ(data=another_list, context={"module": bk_module}, many=True)
        serializer.is_valid(raise_exception=True)
        another_config_vars = serializer.validated_data

        ret = ConfigVarManager().apply_vars_to_module(bk_module, another_config_vars)
        assert (ret.create_num, ret.overwrited_num, ret.ignore_num) == (0, 10, 0)

    @pytest.mark.parametrize(
        ("config_vars", "order_by", "expected"),
        [
            (
                [
                    dict(key="A", value="1", environment_name="prod", description="first"),
                    dict(key="B", value="2", environment_name="stag", description="second"),
                    dict(key="C", value="3", environment_name="stag", description=None),
                ],
                "-created",
                [
                    PlainConfigVar(key="C", value="3", environment_name="stag", description=""),
                    PlainConfigVar(key="B", value="2", environment_name="stag", description="second"),
                    PlainConfigVar(key="A", value="1", environment_name="prod", description="first"),
                ],
            ),
            (
                [
                    dict(key="C", value="3", environment_name="stag", description=None),
                    dict(key="B", value="2", environment_name="stag", description="second"),
                    dict(key="A", value="1", environment_name="prod", description="first"),
                ],
                "-created",
                [
                    PlainConfigVar(key="A", value="1", environment_name="prod", description="first"),
                    PlainConfigVar(key="B", value="2", environment_name="stag", description="second"),
                    PlainConfigVar(key="C", value="3", environment_name="stag", description=""),
                ],
            ),
            (
                [
                    dict(key="A", value="1", environment_name="prod", description="first"),
                    dict(key="B", value="2", environment_name="stag", description="second"),
                    dict(key="C", value="3", environment_name="stag", description=None),
                ],
                "-key",
                [
                    PlainConfigVar(key="C", value="3", environment_name="stag", description=""),
                    PlainConfigVar(key="B", value="2", environment_name="stag", description="second"),
                    PlainConfigVar(key="A", value="1", environment_name="prod", description="first"),
                ],
            ),
        ],
    )
    def test_export_config_vars(self, bk_module, config_var_maker, config_vars, order_by, expected):
        for var in config_vars:
            config_var_maker(module=bk_module, **var)

        all_config_vars = list(bk_module.configvar_set.all().order_by(order_by))
        exported = ExportedConfigVars.from_list(all_config_vars)
        assert exported.env_variables == expected

    @pytest.mark.parametrize(
        ("vars_in_db", "new_vars", "expected_result"),
        [
            (
                # 更新已有数据
                [dict(id=1, key="A", value="2", description="A", environment_name="stag")],
                [dict(id=1, key="A1", value="2", description="A", environment_name="_global_")],
                (0, 1, 0),
            ),
            (
                # 修改、删除、新增数据
                [
                    dict(id=1, key="A", value="2", description="A", environment_name="stag"),
                    dict(id=2, key="B", value="2", description="A", environment_name="stag"),
                ],
                [
                    dict(id=1, key="A1", value="2", description="A", environment_name="_global_"),
                    dict(key="C", value="2", description="B", environment_name="prod"),
                ],
                (1, 1, 1),
            ),
            (
                # 修改(但 id 不在 db 内)、删除数据
                [
                    dict(id=1, key="A", value="2", description="A", environment_name="stag"),
                    dict(id=2, key="B", value="2", description="A", environment_name="stag"),
                ],
                [dict(id=3, key="A1", value="2", description="A", environment_name="_global_")],
                (1, 0, 2),
            ),
        ],
    )
    def test_batch_save(self, bk_module, config_var_maker, vars_in_db, new_vars, expected_result):
        for var in vars_in_db:
            config_var_maker(module=bk_module, **var)

        instance_list = bk_module.configvar_set.filter(is_builtin=False).prefetch_related("environment")
        instance_mapping = {obj.id: obj for obj in instance_list}
        serializer = ConfigVarBatchInputSLZ(
            data=new_vars,
            context={"module": bk_module, "instance_mapping": instance_mapping},
            many=True,
        )
        serializer.is_valid(raise_exception=True)
        valid_new_vars = serializer.validated_data

        # 测试批量保存
        ret = ConfigVarManager().batch_save(bk_module, valid_new_vars)
        assert (ret.create_num, ret.overwrited_num, ret.deleted_num) == expected_result

        # 验证保存后的数据，是否与新输入的数据完全一致
        var_in_db = bk_module.configvar_set.all().order_by("key")
        var_list_in_db = [model_to_dict(_d, fields=CONFIG_VAR_INPUT_FIELDS) for _d in var_in_db]

        valid_new_vars_list = [model_to_dict(_d, fields=CONFIG_VAR_INPUT_FIELDS) for _d in valid_new_vars]
        sorted_valid_new_vars = sorted(valid_new_vars_list, key=lambda x: x["key"])
        assert var_list_in_db == sorted_valid_new_vars

    def test_remove_bulk(self, bk_module, config_var_maker):
        config_var_maker(key="KEY1", value="foo", environment_name="stag", module=bk_module)
        config_var_maker(key="KEY2", value="foo", environment_name="prod", module=bk_module)
        config_var_maker(key="KEY3", value="foo", environment_name="prod", module=bk_module)
        assert bk_module.configvar_set.count() == 3

        assert ConfigVarManager().remove_bulk(bk_module, exclude_keys=["KEY1", "KEY4"]) == 2
        assert bk_module.configvar_set.count() == 1
        assert bk_module.configvar_set.first().key == "KEY1"


class TestConfigVarFormatSLZ:
    @pytest.mark.parametrize(
        "params",
        [{"key": "foo"}, {"key": "KUBERNETES_FOO"}, {"key": "BKPAAS_FOO"}, {"description": "x" * 201}],
    )
    def test_key_error(self, bk_module, random_config_var_maker, params):
        serializer = ConfigVarBaseInputSLZ(
            data=random_config_var_maker(**params, environment_name="stag"), context={"module": bk_module}
        )
        with pytest.raises(ValidationError):
            serializer.is_valid(raise_exception=True)


class TestExportedConfigVars:
    @pytest.mark.parametrize(
        ("env_variables", "expected"),
        [
            (
                [],
                dedent(
                    """\
            # 环境变量文件字段说明：
            #   - key: 变量名称，仅支持大写字母、数字、下划线
            #   - value: 变量值
            #   - description: 描述文字
            #   - environment_name: 生效环境
            #     - 可选值:
            #       - stag: 预发布环境
            #       - prod: 生产环境
            #       - _global_: 所有环境
            env_variables: []
            """
                ),
            ),
            (
                [
                    PlainConfigVar(key="STAG", value="example", description="example", environment_name="stag"),
                    PlainConfigVar(key="PROD", value="example", description="example", environment_name="prod"),
                    PlainConfigVar(key="GLOBAL", value="example", description="example", environment_name="_global_"),
                ],
                dedent(
                    """\
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
            - description: example
              environment_name: stag
              key: STAG
              value: example
            - description: example
              environment_name: prod
              key: PROD
              value: example
            - description: example
              environment_name: _global_
              key: GLOBAL
              value: example
            """
                ),
            ),
        ],
    )
    def test_to_file_content(self, env_variables, expected):
        assert ExportedConfigVars(env_variables=env_variables).to_file_content() == expected


class TestConfigVarTenantId:
    @pytest.fixture()
    def bk_module_with_tenant(self, bk_module):
        """给模块添加随机 tenant_id"""
        bk_module.tenant_id = get_random_string(length=12, allowed_chars=ascii_uppercase)
        bk_module.save()
        return bk_module

    def test_tenant_id_consistency_on_create(self, bk_module_with_tenant):
        """单个添加环境变量"""
        test_data = {
            "key": "TEST_KEY",
            "value": "test_value",
            "environment_name": "prod",
            "description": "test description",
        }

        slz = ConfigVarSLZ(data=test_data, context={"module": bk_module_with_tenant})
        slz.is_valid(raise_exception=True)
        var = slz.save()

        # 验证 tenant_id 是否与所属模块一致
        db_var = ConfigVar.objects.get(id=var.id)
        assert db_var.tenant_id == bk_module_with_tenant.tenant_id

    def test_tenant_id_consistency_on_batch(self, bk_module_with_tenant, random_config_var_maker):
        """批量编辑环境变量"""
        test_data = [random_config_var_maker(environment_name="prod") for _ in range(3)]

        instance_list = bk_module_with_tenant.configvar_set.filter(is_builtin=False).prefetch_related("environment")
        instance_mapping = {obj.id: obj for obj in instance_list}
        serializer = ConfigVarBatchInputSLZ(
            data=test_data,
            context={"module": bk_module_with_tenant, "instance_mapping": instance_mapping},
            many=True,
        )
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data
        # 执行批量保存
        ConfigVarManager().batch_save(bk_module_with_tenant, valid_data)

        # 验证 tenant_id 是否与所属模块一致
        assert (
            ConfigVar.objects.filter(module=bk_module_with_tenant, tenant_id=bk_module_with_tenant.tenant_id).count()
            == 3
        )
