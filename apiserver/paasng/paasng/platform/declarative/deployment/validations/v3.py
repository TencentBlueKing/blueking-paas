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

import cattr
from rest_framework import serializers

from paasng.platform.applications.serializers.fields import SourceDirField
from paasng.platform.bkapp_model.serializers import v1alpha2
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.serializers import validate_language
from paasng.platform.modules.serializers import ModuleNameField

module_name_field = ModuleNameField()


class DeploymentDescSLZ(serializers.Serializer):
    language = serializers.CharField(help_text="模块开发语言", validators=[validate_language])
    sourceDir = SourceDirField(help_text="源码目录", source="source_dir")
    spec = v1alpha2.BkAppSpecInputSLZ(required=True)

    def to_internal_value(self, data) -> DeploymentDesc:
        attrs = super().to_internal_value(data)
        return cattr.structure(
            {
                "language": attrs["language"],
                "source_dir": attrs["source_dir"],
                "spec_version": AppSpecVersion.VER_3,
                "spec": attrs["spec"],
            },
            DeploymentDesc,
        )
