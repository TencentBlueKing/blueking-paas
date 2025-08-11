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

from dataclasses import asdict
from typing import Dict

from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.version_services import get_version_service
from paasng.utils.validators import RE_CONFIG_VAR_KEY


class DevSandboxListOutputSLZ(serializers.Serializer):
    code = serializers.CharField(help_text="沙箱唯一标识")
    module_name = serializers.CharField(help_text="模块名称", source="module.name")
    version_info = serializers.SerializerMethodField(help_text="版本信息")
    expired_at = serializers.DateTimeField(help_text="过期时间")
    created_at = serializers.DateTimeField(help_text="创建时间", source="created")

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_version_info(self, obj: DevSandbox) -> Dict[str, str]:
        return asdict(obj.version_info) if obj.version_info else {}


class SourceCodeVersionInfoSLZ(serializers.Serializer):
    """源代码配置"""

    version_type = serializers.CharField(help_text="版本类型，目前只能是分支")
    version_name = serializers.CharField(help_text="分支名称")
    revision = serializers.CharField(help_text="版本信息, 如 32 位 hash")

    def validate(self, info: VersionInfo) -> VersionInfo:
        # 所有版本信息字段都需要指定非空值
        if not (info.version_type and info.version_name and info.revision):
            return info

        if info.version_type != VersionType.BRANCH:
            raise ValidationError(_("目前仅支持使用代码分支来创建沙箱"))

        version_service = get_version_service(self.context["module"], operator=self.context["operator"])
        # 逐个检查，确保指定的版本信息的合法性
        for ver in version_service.list_alternative_versions():
            if ver.type == VersionType.BRANCH and info.version_name == ver.name and info.revision == ver.revision:
                return info

        raise ValidationError(_("版本信息错误，请选择正确的仓库分支"))

    def to_internal_value(self, data: Dict[str, str]) -> VersionInfo:
        try:
            return VersionInfo(**data)
        except Exception:
            raise ValidationError(_("版本信息格式错误"))


class DevSandboxCreateInputSLZ(serializers.Serializer):
    enable_code_editor = serializers.BooleanField(help_text="是否启用代码编辑器", default=False)
    inject_staging_env_vars = serializers.BooleanField(help_text="是否注入预发布环境变量", default=False)
    source_code_version_info = SourceCodeVersionInfoSLZ(help_text="源代码配置", required=False)
    enabled_addons_services = serializers.ListField(
        help_text="启用的增强服务", child=serializers.CharField(), required=False
    )


class DevSandboxCreateOutputSLZ(serializers.Serializer):
    code = serializers.CharField(help_text="沙箱唯一标识")


class DevSandboxRepoInfoSLZ(serializers.Serializer):
    url = serializers.CharField(help_text="代码仓库地址")
    version_info = SourceCodeVersionInfoSLZ(help_text="代码版本信息")


class DevSandboxRetrieveOutputSLZ(serializers.Serializer):
    workspace = serializers.CharField(help_text="沙箱工作目录")

    devserver_token = serializers.CharField(help_text="devserver 服务 token")
    code_editor_password = serializers.CharField(help_text="代码编辑器访问密码", allow_null=True)
    env_vars = serializers.JSONField(help_text="沙箱环境变量")

    repo = DevSandboxRepoInfoSLZ(help_text="代码仓库信息")
    app_url = serializers.CharField(help_text="SaaS 服务地址", source="urls.app")
    devserver_url = serializers.CharField(help_text="devserver 服务地址", source="urls.devserver")
    code_editor_url = serializers.CharField(help_text="code editor 服务地址", source="urls.code_editor")

    status = serializers.ChoiceField(choices=DevSandboxStatus.get_django_choices(), help_text="运行状态")


class DevSandboxCommitInputSLZ(serializers.Serializer):
    message = serializers.CharField(max_length=256, help_text="代码提交（Commit）信息")


class DevSandboxCommitOutputSLZ(serializers.Serializer):
    repo_url = serializers.CharField(help_text="代码仓库地址")


class DevSandboxPreDeployCheckOutputSLZ(serializers.Serializer):
    result = serializers.BooleanField(help_text="预部署检查结果")


class DevSandboxEnvVarsUpsertInputSLZ(serializers.Serializer):
    key = serializers.RegexField(
        RE_CONFIG_VAR_KEY,
        max_length=1024,
        required=True,
        error_messages={"invalid": _("格式错误，只能以大写字母开头，由大写字母、数字与下划线组成。")},
    )
    value = serializers.CharField(max_length=255, help_text="环境变量值")


class DevSandboxEnvVarsListOutputSLZ(serializers.Serializer):
    key = serializers.CharField(help_text="环境变量键名")
    value = serializers.CharField(help_text="环境变量值")
    source = serializers.CharField(help_text="环境变量来源")
