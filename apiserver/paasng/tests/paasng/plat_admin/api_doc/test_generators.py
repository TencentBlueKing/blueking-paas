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

"""swagger 文档的生成测试

drf-yasg 以 serializer 的 ref_name (缺省为类名) 作为 definitions 中的 key, 文档是全局扁平的一张表,
所以 ref_name 必须全局唯一.

冲突分两种, 危害不同, 需要分别覆盖:

1. 隐式冲突: 两个同名 serializer 都没显式声明 Meta.ref_name, drf-yasg 生成时会抛 SwaggerGenerationError,
   表现为 /docs/ 整体打不开.
2. 显式冲突: 两个不同的 serializer 显式声明了同一个 Meta.ref_name. 此时 drf-yasg **不会报错**,
   后注册的 schema 会被直接丢弃, 文档静默出错.
"""

from collections import defaultdict
from unittest import mock

import pytest
from drf_yasg import openapi
from drf_yasg.inspectors import field as field_inspector
from drf_yasg.utils import get_serializer_class
from rest_framework import serializers

from paasng.plat_admin.api_doc.generators import OpenAPISchemaGenerator


def _generate_schema_and_collect_ref_names() -> tuple[dict, dict[str, set[type]]]:
    """生成全量 schema, 同时记录每个 ref_name 实际被哪些 serializer 使用

    :return: (schema, {ref_name: {serializer 类}})
    """
    used_ref_names: dict[str, set[type]] = defaultdict(set)
    original_get_serializer_ref_name = field_inspector.get_serializer_ref_name

    def _record_ref_name(serializer: serializers.BaseSerializer) -> str:
        ref_name = original_get_serializer_ref_name(serializer)
        if ref_name:
            used_ref_names[ref_name].add(get_serializer_class(serializer))
        return ref_name

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="t", default_version="v"))
    # public=True 会跳过权限过滤, 从而覆盖全部 endpoint
    with mock.patch.object(field_inspector, "get_serializer_ref_name", _record_ref_name):
        schema = generator.get_schema(request=None, public=True)
    return schema, used_ref_names


@pytest.fixture()
def schema_and_ref_names() -> tuple[dict, dict[str, set[type]]]:
    """生成一次全量 schema"""
    return _generate_schema_and_collect_ref_names()


def test_generate_schema_successfully(schema_and_ref_names):
    """全量生成 schema 不应抛异常, 否则整个 swagger 页面无法打开"""
    schema, _ = schema_and_ref_names

    assert schema["paths"]
    assert schema["definitions"]


def test_ref_name_is_unique_in_definitions(schema_and_ref_names):
    """同一个 ref_name 不能被多个 serializer 使用, 否则文档会静默丢失其中一个的定义"""
    _, used_ref_names = schema_and_ref_names

    conflicts = {
        ref_name: sorted(f"{slz.__module__}.{slz.__name__}" for slz in slzs)
        for ref_name, slzs in used_ref_names.items()
        if len(slzs) > 1
    }
    assert not conflicts
