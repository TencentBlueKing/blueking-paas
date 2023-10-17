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
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PDValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.models import to_error_string
from paas_wl.workloads.images.serializers import ImageCredentialSLZ
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.serializers import (
    CreateModuleBuildConfigSLZ,
    ModuleSourceConfigSLZ,
    validate_build_method,
)

from .mixins import AdvancedCreationParamsMixin, AppBasicInfoMixin


class CloudNativeParamsSLZ(serializers.Serializer):
    """创建云原生应用的详细参数"""

    image = serializers.CharField(label=_('容器镜像地址'), required=True)
    command = serializers.ListField(help_text=_('启动命令'), child=serializers.CharField(), required=False, default=list)
    args = serializers.ListField(help_text=_('命令参数'), child=serializers.CharField(), required=False, default=list)
    target_port = serializers.IntegerField(label=_('容器端口'), required=False)
    # 在前端页面调整完成前，先保持默认值为 v1alpha1 以兼容现有逻辑
    api_version = serializers.CharField(label=_('API版本'), required=False, default=ApiVersion.V1ALPHA1.value)


class CreateCloudNativeAppSLZ(AppBasicInfoMixin):
    """创建云原生架构应用的表单"""

    # [Deprecated] cloud_native_params is deprecated, use param manifest instead
    cloud_native_params = CloudNativeParamsSLZ(label=_('云原生应用参数'), required=False)
    advanced_options = AdvancedCreationParamsMixin(required=False)

    source_config = ModuleSourceConfigSLZ(required=False, help_text=_('源码配置'))
    image_credentials = ImageCredentialSLZ(required=False, help_text=_('镜像凭证信息'))
    build_config = CreateModuleBuildConfigSLZ(required=False, help_text=_('构建配置'))
    manifest = serializers.JSONField(required=False, help_text=_('云原生应用 manifest'))

    def validate(self, attrs):
        super().validate(attrs)

        # 兼容旧逻辑，支持仅传 cloud_native_params 即可创建应用
        if attrs.get('cloud_native_params'):
            return attrs

        source_cfg = attrs.get('source_config')
        if not source_cfg:
            raise ValidationError(_('需要指定 源码配置'))

        build_config = attrs.get('build_config')
        if not build_config:
            raise ValidationError("missing build_config field")

        source_origin = source_cfg['source_origin']
        validate_build_method(build_config.build_method, source_origin)

        if manifest := attrs.get('manifest'):
            # 检查 source_config 中 source_origin 类型必须为 CNATIVE_IMAGE
            if source_origin != SourceOrigin.CNATIVE_IMAGE:
                raise ValidationError(_('托管模式为仅镜像时，source_origin 必须为 CNATIVE_IMAGE'))

            try:
                bkapp_res = BkAppResource(**manifest)
            except PDValidationError as e:
                raise ValidationError(to_error_string(e))

            if bkapp_res.apiVersion != ApiVersion.V1ALPHA2:
                raise ValidationError(_('请使用 BkApp v1alpha2 版本'))

            if bkapp_res.metadata.name != attrs["code"]:
                raise ValidationError(_("Manifest 中定义的应用模型名称与应用ID不一致"))

            if bkapp_res.spec.build is None or bkapp_res.spec.build.image != source_cfg['source_repo_url']:
                raise ValidationError(_('Manifest 中定义的镜像信息与 source_repo_url 不一致'))
        return attrs
