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

from typing import Any, Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.serializers import BkAppSpecSLZ, ModuleSourceConfigSLZ, validate_build_method

from .app import ApplicationSLZ
from .mixins import AdvancedCreationParamsMixin, AppBasicInfoMixin, MarketParamsMixin


class ApplicationCreateInputV2SLZ(AppBasicInfoMixin):
    """普通应用创建应用表单，目前产品上已经没有入口，但是暂时先保留 API"""

    type = serializers.ChoiceField(
        choices=ApplicationType.get_django_choices(), default=ApplicationType.CLOUD_NATIVE.value
    )
    engine_enabled = serializers.BooleanField(default=True, required=False)
    engine_params = ModuleSourceConfigSLZ(required=False)
    advanced_options = AdvancedCreationParamsMixin(required=False)
    is_plugin_app = serializers.BooleanField(default=False)
    is_ai_agent_app = serializers.BooleanField(default=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        super().validate(attrs)

        if attrs["engine_enabled"] and not attrs.get("engine_params"):
            raise ValidationError(_("应用引擎参数未提供"))

        # Be compatible with current application creation page, should be removed when new design was published
        if not attrs["engine_enabled"]:
            attrs["type"] = ApplicationType.ENGINELESS_APP.value
        elif attrs["type"] == ApplicationType.ENGINELESS_APP.value:
            raise ValidationError(_('已开启引擎，类型不能为 "engineless_app"'))

        return attrs


class CloudNativeAppCreateInputSLZ(AppBasicInfoMixin):
    """创建云原生架构应用的表单"""

    source_config = ModuleSourceConfigSLZ(required=True, help_text=_("源码/镜像配置"))
    bkapp_spec = BkAppSpecSLZ()
    advanced_options = AdvancedCreationParamsMixin(required=False)
    is_plugin_app = serializers.BooleanField(default=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = super().validate(attrs)

        src_cfg = attrs["source_config"]
        build_cfg = attrs["bkapp_spec"]["build_config"]

        validate_build_method(build_cfg.build_method, src_cfg["source_origin"])

        repo_url = src_cfg.get("source_repo_url")
        if build_cfg.build_method == RuntimeType.CUSTOM_IMAGE and build_cfg.image_repository != repo_url:
            raise ValidationError("image_repository is not consistent with source_repo_url")

        self._validate_image_credential(build_cfg.image_credential)

        return attrs

    def _validate_image_credential(self, image_credential: Dict[str, str] | None):
        if not image_credential:
            return

        if not image_credential.get("password") or not image_credential.get("username"):
            raise ValidationError("image credential missing valid username and password")


class LessCodeAppCreateInputSLZ(AppBasicInfoMixin):
    """创建 LessCode 应用"""

    engine_params = ModuleSourceConfigSLZ(required=True)

    def validate_engine_params(self, engine_params):
        if not engine_params.get("source_init_template"):
            raise ValidationError("source_init_template is required in engine_params")

        engine_params["source_origin"] = SourceOrigin.BK_LESS_CODE
        return engine_params

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        data.update(
            {
                # 新建的 LessCode 应用都为云原生应用
                "type": ApplicationType.CLOUD_NATIVE.value,
                "engine_enabled": True,
                "is_ai_agent_app": False,
                "is_plugin_app": False,
            }
        )

        return data


class AIAgentAppCreateInputSLZ(AppBasicInfoMixin):
    """创建 AI Agent 应用"""

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        data.update(
            {
                "is_ai_agent_app": True,
                # AI Agent 应用也是一个插件，需要自动注册网关
                "is_plugin_app": True,
                "type": ApplicationType.CLOUD_NATIVE.value,
                "engine_enabled": True,
            }
        )

        return data


class ThirdPartyAppCreateInputSLZ(AppBasicInfoMixin):
    """创建第三方（外链）应用"""

    engine_enabled = serializers.BooleanField(default=False)
    market_params = MarketParamsMixin()

    def validate(self, attrs):
        if attrs["engine_enabled"]:
            raise ValidationError(_("该接口只支持创建外链应用"))
        return attrs


class SourceInitResultSLZ(serializers.Serializer):
    """源码初始化结果"""

    code = serializers.CharField(help_text="状态码", default="OK", allow_blank=True)
    extra_info = serializers.DictField(help_text="额外信息，包含下载地址等", default=dict, allow_null=True)
    dest_type = serializers.CharField(help_text="目标存储类型", allow_null=True, default=None)
    error = serializers.CharField(help_text="错误信息", allow_blank=True, default="")


class ApplicationCreateOutputSLZ(serializers.Serializer):
    """应用创建成功后的返回结果"""

    application = ApplicationSLZ(help_text="应用详情")
    source_init_result = SourceInitResultSLZ(help_text="源码初始化结果", allow_null=True, default=dict)


class AdvancedRegionClusterSLZ(serializers.Serializer):
    """高级创建选项中的集群信息"""

    region = serializers.CharField(help_text="区域名称")
    env_cluster_names = serializers.JSONField(help_text="各环境集群名称")


class CreationOptionsOutputSLZ(serializers.Serializer):
    """应用创建选项"""

    allow_adv_options = serializers.BooleanField(help_text="是否允许使用高级创建选项")
    adv_region_clusters = serializers.ListField(help_text="高级创建选项中的集群信息", child=AdvancedRegionClusterSLZ())
