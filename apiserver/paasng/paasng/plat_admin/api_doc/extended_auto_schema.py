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
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import FileUploadParser, force_serializer_instance, get_object_classes
from pydantic import BaseModel


def get_consumes(parser_classes):
    """Extract ``consumes`` MIME types from a list of parser classes.

    :param list parser_classes: parser classes
    :type parser_classes: list[rest_framework.parsers.BaseParser or type[rest_framework.parsers.BaseParser]]
    :return: MIME types for ``consumes``
    :rtype: list[str]
    """
    parser_classes = get_object_classes(parser_classes)
    parser_classes = [pc for pc in parser_classes if not issubclass(pc, FileUploadParser)]
    media_types = [parser.media_type for parser in parser_classes or []]
    return media_types


def registry_definitions(schema: openapi.Schema, global_components: openapi.ReferenceResolver):
    if definitions := schema.get("definitions"):
        global_components["definitions"].update(definitions)
    if properties := schema.get("properties"):
        for value in properties.values():
            if isinstance(value, openapi.Schema):
                registry_definitions(value, global_components)
    if (items := schema.get("items")) and isinstance(items, openapi.Schema):
        registry_definitions(items, global_components)


class ExtraDefinitionsInspectorMixin:
    """把自定义Responses中的schema definition添加到全局的Definitions"""

    def get_response_serializers(self: SwaggerAutoSchema):
        overrides_responses = self.overrides.get("responses", None)
        if overrides_responses:
            for sc, resp in overrides_responses.items():
                # 判断是否继承自 BaseModel
                if isinstance(resp, type) and issubclass(resp, BaseModel):
                    # 得益于 pydantic 原生支持 Swagger/OpenAPI 规范, 这里的类型转换完全兼容
                    schema = openapi.Schema(**resp.schema())
                    overrides_responses[sc] = schema
                    registry_definitions(schema, self.components)
                if isinstance(resp, openapi.Schema):
                    schema = resp
                    registry_definitions(schema, self.components)

        return super().get_response_serializers()  # type: ignore


class BaseModelRequestBodyInspectorMixin:
    """将 swagger_auto_schema 中继承自 pydantic.BaseModel 的 request_body 转换成 drf_yasg.openapi.Schema"""

    def _get_request_body_override(self: SwaggerAutoSchema):
        body_override = self.overrides.get("request_body", None)
        # 判断是否继承自 BaseModel
        if body_override and isinstance(body_override, type) and issubclass(body_override, BaseModel):
            # 得益于 pydantic 原生支持 Swagger/OpenAPI 规范, 这里的类型转换完全兼容
            schema = openapi.Schema(**body_override.schema())
            registry_definitions(schema, self.components)
            return schema
        return super()._get_request_body_override()  # type: ignore


class ExtendedSwaggerAutoSchema(BaseModelRequestBodyInspectorMixin, ExtraDefinitionsInspectorMixin, SwaggerAutoSchema):
    """自定义的 schema 生成器"""

    def get_consumes(self):
        if "parser_classes" in self.overrides:
            return get_consumes(self.overrides["parser_classes"])
        return super().get_consumes()

    def get_default_response_serializer(self):
        # NOTE: fix a bug of drf-yasg
        # drf-yasg use request_body in get_default_response_serializer
        # but they allow raise Exception in method `_get_request_body_override`
        response_serializer = self.overrides.get("response_serializer", None)
        if response_serializer:
            if isinstance(response_serializer, openapi.Schema.OR_REF):
                return response_serializer
            return force_serializer_instance(response_serializer)
        return super().get_default_response_serializer()
