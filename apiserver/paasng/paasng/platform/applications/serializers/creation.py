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

from typing import Any, Dict

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import OP_TYPE_TENANT_ID
from paasng.core.tenant.utils import AppTenantInfo, stub_app_tenant_info
from paasng.infras.accounts.models import UserProfile
from paasng.platform.applications.constants import ApplicationType, DeployPolicy
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.serializers import BkAppSpecSLZ, ModuleSourceConfigSLZ, validate_build_method
from paasng.utils.i18n.serializers import I18NExtend, i18n

from .app import ApplicationSLZ
from .fields import AppIDField, AppNameField
from .mixins import AdvancedCreationParamsMixin, AppBasicInfoMixin, AppTenantMixin, MarketParamsMixin

# 应用态创建 AI Agent 时要求的 code 前缀。不写入 RESERVED_APP_CODE_PREFIXES，用户态规则保持不变。
AI_AGENT_APP_CODE_PREFIX = "ai-"


def apply_ai_agent_create_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """按 is_engineless / is_isolated 写入与用户态一致的应用标记。"""
    # 两种 AI Agent 应用都标记 is_ai_agent_app=True
    data["is_ai_agent_app"] = True

    if data.get("is_engineless"):
        # 占位外链应用：无引擎、非插件、不可部署
        data["is_plugin_app"] = False
        data["type"] = ApplicationType.ENGINELESS_APP.value
        data["engine_enabled"] = False
    else:
        # 可部署的插件应用：部署时会自动注册网关（bp-{app_code}）
        data["is_plugin_app"] = True
        data["type"] = ApplicationType.CLOUD_NATIVE.value
        data["engine_enabled"] = True
        data["deploy_policy"] = (
            DeployPolicy.ISOLATED.value if data.pop("is_isolated", False) else DeployPolicy.DEFAULT.value
        )

    return data


def validate_ai_agent_create_mode(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """校验 git / 外链 / 模板包三种模式的互斥字段。"""

    # 外链与 git / 隔离部署互斥，避免静默丢掉调用方传入的源码或构建配置。
    if attrs.get("is_engineless"):
        conflicts = [
            name for name in ("source_config", "bkapp_spec") if attrs.get(name)
        ]
        if attrs.get("is_isolated"):
            conflicts.append("is_isolated")

        if conflicts:
            raise ValidationError(
                {name: _("外链模式不能同时指定该字段") for name in conflicts}
            )

        return attrs

    source_config = attrs.get("source_config")
    if not source_config:
        return attrs

    # 空 source_config 会带上 AUTHORIZED_VCS 默认值，必须再核对来源和仓库地址，避免半成品进创建链路。
    if SourceOrigin(source_config["source_origin"]) != SourceOrigin.AUTHORIZED_VCS:
        raise ValidationError(_("使用 git 仓库部署时 source_origin 必须为授权代码库"))

    # 用户态允许 auto_create_repo 由平台建仓；未代建时必须自带仓库地址。
    if not source_config.get("auto_create_repo") and not source_config.get("source_repo_url"):
        raise ValidationError(_("使用 git 仓库部署时必须提供 source_repo_url"))

    if not attrs.get("bkapp_spec"):
        raise ValidationError(_("使用 git 仓库部署时必须提供 bkapp_spec 构建配置"))

    build_cfg = attrs["bkapp_spec"]["build_config"]

    # AI Agent 应用不支持 custom_image（纯镜像托管）
    if build_cfg.build_method == RuntimeType.CUSTOM_IMAGE:
        raise ValidationError(_("AI Agent 应用不支持 custom_image 构建方式"))

    validate_build_method(build_cfg.build_method, source_config["source_origin"])
    return attrs


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
        attrs = super().validate(attrs)

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
    """创建 AI Agent 应用

    默认使用固定模板包（bk-ai-plugin-python）+ buildpack 部署。若传入 source_config，则
    改为使用 git 仓库源码部署，并可通过 bkapp_spec.build_config 选择 buildpack / dockerfile
    构建方式（两者解耦，任意 AI Agent 应用均可使用 git 仓库部署）。

    新增 is_engineless 参数：当设置为 true 时，创建无引擎的外链 AI Agent 应用，
    该应用在用户列表中不可见（is_ai_agent_app=True + type=engineless_app 的组合会被自动过滤），
    仅可通过直接链接访问，支持成员管理（添加/删除管理员）。
    """

    is_isolated = serializers.BooleanField(default=False, help_text="是否部署到隔离环境")
    is_engineless = serializers.BooleanField(default=False, help_text="是否创建为无引擎外链应用，用户列表不可见")
    # 以下参数为选填，不传则走原有固定模板包流程（向后兼容）
    source_config = ModuleSourceConfigSLZ(required=False, help_text=_("git 源码配置，传入则使用 git 仓库部署"))
    bkapp_spec = BkAppSpecSLZ(required=False, help_text=_("构建配置，配合 source_config 使用"))

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return apply_ai_agent_create_defaults(data)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = super().validate(attrs)
        return validate_ai_agent_create_mode(attrs)


@i18n
class SysAIAgentAppCreateInputSLZ(AppTenantMixin):
    """应用态创建 AI Agent 应用，管理员取已注册的 operator。"""

    code = AppIDField()
    name = I18NExtend(AppNameField())
    operator = serializers.CharField(required=True, help_text="已在开发者中心注册的管理员用户名")
    is_isolated = serializers.BooleanField(default=False, help_text="是否部署到隔离环境")
    is_engineless = serializers.BooleanField(default=False, help_text="是否创建为无引擎外链应用，用户列表不可见")
    source_config = ModuleSourceConfigSLZ(required=False, help_text=_("git 源码配置，传入则使用 git 仓库部署"))
    bkapp_spec = BkAppSpecSLZ(required=False, help_text=_("构建配置，配合 source_config 使用"))

    def to_internal_value(self, data):
        # AppNameField 在字段校验阶段就要租户范围，AppTenantMixin.validate 发生在字段校验之后。
        if not settings.ENABLE_MULTI_TENANT_MODE:
            self.context["app_tenant_id"] = stub_app_tenant_info().app_tenant_id
        else:
            self.context["app_tenant_id"] = data.get("app_tenant_id", "")

        ret = super().to_internal_value(data)
        return apply_ai_agent_create_defaults(ret)

    def validate_code(self, code: str) -> str:
        # 应用态单独要求 ai- 前缀，不写入保留前缀列表，避免改变用户态创建规则。
        if not code.startswith(AI_AGENT_APP_CODE_PREFIX):
            raise ValidationError(_("应用 ID 必须以 {prefix} 开头").format(prefix=AI_AGENT_APP_CODE_PREFIX))

        return code

    def validate_operator(self, operator: str) -> str:
        user_id = user_id_encoder.encode(settings.USER_TYPE, operator)

        # UserProfile 在用户首次访问开发者中心时创建，用它判定已登录/注册过。不造虚拟用户。
        if not UserProfile.objects.filter(user=user_id).exists():
            raise ValidationError(_("用户未在开发者中心注册"))

        return operator

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = super().validate(attrs)
        attrs = validate_ai_agent_create_mode(attrs)
        self._reject_vcs_delegation(attrs)

        # AppTenantMixin 已写入 mode/id/tenant_id，组装给创建链路使用。
        app_tenant_info = AppTenantInfo(
            app_tenant_mode=attrs["app_tenant_mode"],
            app_tenant_id=attrs["app_tenant_id"],
            tenant_id=attrs["tenant_id"],
        )
        attrs["app_tenant_info"] = app_tenant_info

        user_id = user_id_encoder.encode(settings.USER_TYPE, attrs["operator"])
        profile = UserProfile.objects.get(user=user_id)
        self._validate_operator_tenant(profile, app_tenant_info)
        attrs["operator_user"] = get_user_by_user_id(user_id)
        return attrs

    def _reject_vcs_delegation(self, attrs: Dict[str, Any]) -> None:
        """拒绝借 operator 的 VCS OAuth 代建仓或写模板。"""

        source_config = attrs.get("source_config")
        if not source_config:
            return

        if source_config.get("auto_create_repo"):
            raise ValidationError({"source_config": _("应用态创建不支持由平台代建代码仓库")})

        if source_config.get("write_template_to_repo"):
            raise ValidationError({"source_config": _("应用态创建不支持将模板写入代码仓库")})

        if source_config.get("repo_group") or source_config.get("repo_name"):
            raise ValidationError({"source_config": _("应用态创建不支持指定新建仓库的项目组或名称")})

    def _validate_operator_tenant(self, profile: UserProfile, app_tenant_info: AppTenantInfo) -> None:
        """校验 operator 所属租户与将要创建的应用租户一致。"""

        # 非多租户没有跨租户面，profile 与 stub 租户都是 default。
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return

        # 全租户应用只允许运营租户用户当管理员，对齐用户态 validate_app_tenant_params。
        if app_tenant_info.app_tenant_mode == AppTenantMode.GLOBAL:
            if profile.tenant_id != OP_TYPE_TENANT_ID:
                raise ValidationError({"operator": _("当前不允许创建全租户可用的应用")})
            return

        # 单租户应用的管理员必须属于该应用所属租户。
        if profile.tenant_id != app_tenant_info.tenant_id:
            raise ValidationError({"operator": _("operator 与应用不属于同一租户")})


class ThirdPartyAppCreateInputSLZ(AppBasicInfoMixin):
    """创建第三方（外链）应用"""

    engine_enabled = serializers.BooleanField(default=False)
    market_params = MarketParamsMixin()

    def validate(self, attrs):
        attrs = super().validate(attrs)
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
