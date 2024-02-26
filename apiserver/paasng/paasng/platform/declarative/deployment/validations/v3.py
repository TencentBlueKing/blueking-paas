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
import cattr
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.platform.declarative.application.resources import (
    ModuleDesc,
)
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.serializers import validate_language
from paasng.platform.modules.serializers import ModuleNameField

module_name_field = ModuleNameField()


class ModuleSpecField(serializers.DictField):
    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        return bk_app.BkAppSpec(**attrs)

    def to_representation(self, value):
        if isinstance(value, bk_app.BkAppSpec):
            return value.dict(exclude_none=True, exclude_unset=True)
        return super().to_representation(value)


class ModuleDescriptionSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="模块名称", required=True)
    language = serializers.CharField(help_text="模块开发语言", validators=[validate_language])
    sourceDir = serializers.CharField(help_text="源码目录", default="")
    isDefault = serializers.BooleanField(default=False, help_text="是否为主模块")
    spec = ModuleSpecField(required=True)

    def to_internal_value(self, data) -> ModuleDesc:
        attrs = super().to_internal_value(data)
        return ModuleDesc(**attrs)


class DeploymentDescSLZ(serializers.Serializer):
    module = ModuleDescriptionSLZ()

    def to_internal_value(self, data) -> DeploymentDesc:
        module_desc = super().to_internal_value(data)["module"]
        return cattr.structure(
            {
                "language": module_desc.language,
                "source_dir": module_desc.sourceDir,
                "spec": module_desc.spec,
            },
            DeploymentDesc,
        )
