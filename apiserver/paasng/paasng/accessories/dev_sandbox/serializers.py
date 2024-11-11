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

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from paas_wl.bk_app.dev_sandbox.entities import HealthPhase
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.sourcectl.constants import VersionType


class DevSandboxDetailSLZ(serializers.Serializer):
    """Serializer for dev sandbox detail"""

    url = serializers.CharField(help_text="dev sandbox 服务地址")
    token = serializers.CharField(help_text="访问 dev sandbox 中 devserver 服务的 token")
    status = serializers.ChoiceField(choices=HealthPhase.get_django_choices(), help_text="dev sandbox 的运行状态")


class CreateDevSandboxWithCodeEditorSLZ(serializers.Serializer):
    """Serializer for create dev sandbox"""

    version_type = serializers.ChoiceField(
        choices=VersionType.get_choices(),
        required=True,
        error_messages={"invalid_choice": f"Invalid choice. Valid choices are {VersionType.get_values()}"},
        help_text="版本类型, 如 branch/tag/trunk",
    )
    version_name = serializers.CharField(
        required=True, help_text="版本名称: 如 Tag Name/Branch Name/trunk/package_name"
    )
    revision = serializers.CharField(
        required=False,
        help_text="版本信息, 如 hash(git版本)/version(源码包); 如果根据 smart_revision 能查询到 revision, 则不使用该值",
    )


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
