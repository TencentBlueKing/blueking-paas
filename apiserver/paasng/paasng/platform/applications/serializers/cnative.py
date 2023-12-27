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
from typing import Dict, Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.serializers import BkAppSpecSLZ, ModuleSourceConfigSLZ, validate_build_method

from .mixins import AdvancedCreationParamsMixin, AppBasicInfoMixin


class CreateCloudNativeAppSLZ(AppBasicInfoMixin):
    """创建云原生架构应用的表单"""

    source_config = ModuleSourceConfigSLZ(required=True, help_text=_("源码/镜像配置"))
    bkapp_spec = BkAppSpecSLZ()
    advanced_options = AdvancedCreationParamsMixin(required=False)
    is_plugin_app = serializers.BooleanField(default=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        source_config = attrs["source_config"]
        build_config = attrs["bkapp_spec"]["build_config"]

        validate_build_method(build_config.build_method, source_config["source_origin"])

        if (
            build_config.build_method == RuntimeType.CUSTOM_IMAGE
            and build_config.image_repository != source_config.get("source_repo_url")
        ):
            raise ValidationError("image_repository is not consistent with source_repo_url")

        self._validate_image_credential(build_config.image_credential)

        return attrs

    def _validate_image_credential(self, image_credential: Optional[Dict[str, str]]):
        if not image_credential:
            return

        if not image_credential.get("password") or not image_credential.get("username"):
            raise ValidationError("image credential missing valid username and password")

    def to_internal_value(self, data: Dict):
        data = super().to_internal_value(data)
        # TODO 前端创建插件应用传了正确的 source_init_template 后，去掉这段兼容逻辑
        if data["is_plugin_app"]:
            data["source_init_template"] = "bk-saas-plugin-python"
        return data
