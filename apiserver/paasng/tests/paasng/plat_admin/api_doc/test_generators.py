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

drf-yasg 以 serializer 类名作为 ref_name, 不同模块的同名 serializer 同时进入文档会导致
生成失败 (表现为 /docs/ 整体打不开), 这里全量生成一次 schema 以在 CI 阶段暴露该类问题.
"""

from drf_yasg import openapi

from paasng.plat_admin.api_doc.generators import OpenAPISchemaGenerator


def test_generate_schema_no_ref_name_conflict():
    """全量生成 schema，不应抛出 SwaggerGenerationError 等异常"""
    gen = OpenAPISchemaGenerator(info=openapi.Info(title="t", default_version="v"))
    # public=True 会跳过权限过滤，覆盖全部 endpoint
    schema = gen.get_schema(request=None, public=True)

    assert schema["paths"]
