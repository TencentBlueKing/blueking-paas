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
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from paas_wl.bk_app.dev_sandbox.entities import HealthPhase
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.version_services import get_version_service


class DevSandboxDetailSLZ(serializers.Serializer):
    """Serializer for dev sandbox detail"""

    app_url = serializers.SerializerMethodField(help_text="dev sandbox saas 应用服务地址")
    devserver_url = serializers.SerializerMethodField(help_text="dev sandbox devserver 服务地址")
    token = serializers.CharField(help_text="访问 dev sandbox 中 devserver 服务的 token")
    status = serializers.ChoiceField(choices=HealthPhase.get_django_choices(), help_text="dev sandbox 的运行状态")

    def get_app_url(self, obj: Dict[str, str]) -> str:
        # 拼接 app_url
        return f"{obj['url']}/app/"

    def get_devserver_url(self, obj: Dict[str, str]) -> str:
        # 拼接 devserver_url
        return f"{obj['url']}/devserver/"


class CreateDevSandboxWithCodeEditorSLZ(serializers.Serializer):
    """创建带代码编辑器的沙箱"""

    version_type = serializers.CharField(help_text="版本类型，目前只能是分支")
    version_name = serializers.CharField(help_text="分支名称")
    revision = serializers.CharField(help_text="版本信息, 如 32 位 hash")

    def validate(self, attrs: Dict[str, str]) -> Dict[str, str]:
        if attrs["version_type"] != VersionType.BRANCH:
            raise ValidationError(_("目前仅支持使用代码分支来创建沙箱"))

        version_service = get_version_service(self.context["module"], operator=self.context["operator"])
        # 逐个检查，确保指定的版本信息的合法性
        for ver in version_service.list_alternative_versions():
            if (
                ver.type == VersionType.BRANCH
                and attrs["version_name"] == ver.name
                and attrs["revision"] == ver.revision
            ):
                return attrs

        raise ValidationError(_("版本信息错误，请选择正确的仓库分支"))


class DevSandboxWithCodeEditorUrlsSLZ(serializers.Serializer):
    """Serializer for dev sandbox with code editor urls"""

    app_url = serializers.CharField(help_text="访问 dev sandbox saas 的 url")
    devserver_url = serializers.CharField(help_text="访问 dev sandbox devserver 的 url")
    code_editor_url = serializers.CharField(help_text="访问 dev sandbox code editor 的 url")


class DevSandboxWithCodeEditorDetailSLZ(serializers.Serializer):
    """Serializer for dev sandbox with code editor detail"""

    urls = DevSandboxWithCodeEditorUrlsSLZ()
    token = serializers.CharField(help_text="访问 dev sandbox 中 devserver 服务的 token")
    dev_sandbox_status = serializers.ChoiceField(
        choices=HealthPhase.get_django_choices(), help_text="dev sandbox 的运行状态"
    )
    code_editor_status = serializers.ChoiceField(
        choices=HealthPhase.get_django_choices(), help_text="code editor 的运行状态"
    )
    dev_sandbox_env_vars = serializers.JSONField(default={}, help_text="dev sandbox 环境变量")


class DevSandboxSLZ(serializers.ModelSerializer):
    """Serializer for dev sandbox"""

    module_name = SerializerMethodField()
    version_info_dict = SerializerMethodField()

    class Meta:
        model = DevSandbox
        fields = [
            "id",
            "status",
            "expired_at",
            "version_info_dict",
            "created",
            "updated",
            "module_name",
        ]

    def get_module_name(self, obj: DevSandbox) -> str:
        return obj.module.name

    def get_version_info_dict(self, obj: DevSandbox) -> dict:
        return asdict(obj.version_info)


class DevSandboxCommitInputSLZ(serializers.Serializer):
    """沙箱开发环境代码提交"""

    message = serializers.CharField(help_text="代码提交（Commit）信息")


class DevSandboxCommitOutputSLZ(serializers.Serializer):
    """沙箱开发环境代码提交"""

    repo_url = serializers.CharField(help_text="代码仓库地址")
