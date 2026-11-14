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

import re

from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from paasng.platform.agent_sandbox.models import E2BApiKey, E2BSandboxTemplate
from paasng.utils.serializers import UserNameField

from .constants import (
    CUSTOM_RESOURCE_NAME_SEPARATOR,
    DEFAULT_TEMPLATE_CPU_COUNT,
    DEFAULT_TEMPLATE_MEMORY_MB,
    MAX_TEMPLATE_CPU_COUNT,
    MAX_TEMPLATE_DISK_SIZE_MB,
    MAX_TEMPLATE_MEMORY_MB,
    MIN_TEMPLATE_DISK_SIZE_MB,
    TEMPLATE_ID_PATTERN,
)

_ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class E2BApiKeyCreateInputSLZ(serializers.Serializer):
    name = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default="", help_text="便于区分多枚 key"
    )


class E2BApiKeyOutputSLZ(serializers.ModelSerializer):
    """key 的元信息。不含明文，明文只在签发响应里出现一次。

    不输出 ``enabled`` 与 ``revoked_at``：签发响应和列表都只涉及生效中的 key
    """

    class Meta:
        model = E2BApiKey
        fields = ["uuid", "name", "key_prefix", "created"]
        extra_kwargs = {
            "uuid": {"label": "密钥 ID"},
            "name": {"label": "名称"},
            "key_prefix": {"label": "密钥前缀"},
            "created": {"label": "签发时间"},
        }


class E2BApiKeyCreateOutputSLZ(E2BApiKeyOutputSLZ):
    """签发响应，比列表多一个明文字段。"""

    api_key = serializers.CharField(read_only=True, help_text="明文密钥，仅在本次响应中返回，请妥善保存")

    class Meta(E2BApiKeyOutputSLZ.Meta):
        fields = [*E2BApiKeyOutputSLZ.Meta.fields, "api_key"]


class E2BSandboxCreateInputSLZ(serializers.Serializer):
    """只校验我们必须知道的字段，其余直接交给底层 e2b 网关。

    请求体的字段集由 e2b 协议规定，SDK 版本演进会往里加字段（挂卷、网络策略等）。
    在这里穷举一遍就等于维护第二份 schema，且漏掉的字段会被 DRF 静默丢弃——
    表现为用户传了参数却不生效，比报错更难排查。因此校验之后转发的是原始请求体。
    """

    # 字段名是 e2b 协议规定的驼峰形式，不能改成平台习惯的下划线
    templateID = serializers.CharField(help_text="沙箱模板标识")

    def validate_templateID(self, value: str) -> str:  # noqa: N802
        # 未登记与已下线不作区分，SDK 侧只需要知道这个模板不能用。
        # 不看 is_public：不公开只影响页面展示，服务自用的模板要能通过 SDK 使用
        if not E2BSandboxTemplate.objects.builtins().filter(template_id=value, enabled=True).exists():
            raise serializers.ValidationError(f"template {value} is not available")
        return value


class E2BSandboxTimeoutInputSLZ(serializers.Serializer):
    timeout = serializers.IntegerField(min_value=1, help_text="从此刻起的存活秒数")


class E2BConsoleApiKeyOutputSLZ(E2BApiKeyOutputSLZ):
    """开发者中心页面展示用，比 APIGW 版本多一个签发人。"""

    owner = UserNameField(read_only=True, help_text="签发人")

    class Meta(E2BApiKeyOutputSLZ.Meta):
        fields = [*E2BApiKeyOutputSLZ.Meta.fields, "owner"]


class E2BConsoleSandboxListInputSLZ(serializers.Serializer):
    template_id = serializers.CharField(required=False, help_text="只列出使用该模板的沙箱")


class _GatewayDateTimeField(serializers.DateTimeField):
    """网关返回的是 ISO 8601 字符串，平台的 DateTimeField 只接受 datetime（要转本地时区），需先解析。"""

    def to_representation(self, value):
        if isinstance(value, str):
            value = parse_datetime(value)
        return super().to_representation(value)


class E2BConsoleSandboxOutputSLZ(serializers.Serializer):
    """把网关列表条目转成平台风格的字段。

    按白名单输出：网关条目里的 ``clientID`` 属于内部标识，不下发给页面。
    列表条目本身不含 ``domain`` / ``envdAccessToken``，白名单也保证将来网关加了这些字段时不会被带出去。
    """

    sandbox_id = serializers.CharField(source="sandboxID", help_text="沙箱 ID")
    template_id = serializers.CharField(source="templateID", help_text="模板标识")
    state = serializers.CharField(help_text="运行状态，running / paused")
    cpu_count = serializers.IntegerField(source="cpuCount", help_text="CPU 核数")
    memory_mb = serializers.IntegerField(source="memoryMB", help_text="内存（MB）")
    disk_size_mb = serializers.IntegerField(source="diskSizeMB", help_text="磁盘（MB）")
    started_at = _GatewayDateTimeField(source="startedAt", help_text="启动时间")
    end_at = _GatewayDateTimeField(source="endAt", help_text="预计回收时间")


class E2BConsoleTemplateOutputSLZ(serializers.Serializer):
    """模板列表项"""

    template_id = serializers.CharField(help_text="模板标识，即 SDK 创建沙箱时传入的 templateID")
    name = serializers.CharField(help_text="展示名称")
    description = serializers.CharField(help_text="描述，可能为空字符串")
    cpu_count = serializers.IntegerField(help_text="CPU 核数")
    memory_mb = serializers.IntegerField(help_text="内存（MB）")
    disk_size_mb = serializers.IntegerField(allow_null=True, help_text="系统盘（MB），为空表示未挂载独立系统盘")


class E2BConsoleTemplateDetailOutputSLZ(E2BConsoleTemplateOutputSLZ):
    """模板详情，在列表项基础上增加镜像等信息。"""

    image = serializers.CharField(help_text="镜像")
    prewarm_count = serializers.IntegerField(help_text="每个集群预热的实例数")


class E2BTemplateSpecInputSLZ(serializers.Serializer):
    """模板规格，内置模板与自定义模板共用"""

    name = serializers.CharField(max_length=64, help_text="展示名称")
    description = serializers.CharField(allow_blank=True, default="", help_text="描述")
    image = serializers.CharField(max_length=256, help_text="镜像，须内置 envd")
    cpu_count = serializers.IntegerField(
        min_value=1, max_value=MAX_TEMPLATE_CPU_COUNT, default=DEFAULT_TEMPLATE_CPU_COUNT, help_text="CPU 核数"
    )
    memory_mb = serializers.IntegerField(
        min_value=1, max_value=MAX_TEMPLATE_MEMORY_MB, default=DEFAULT_TEMPLATE_MEMORY_MB, help_text="内存（MB）"
    )
    disk_size_mb = serializers.IntegerField(
        min_value=MIN_TEMPLATE_DISK_SIZE_MB,
        max_value=MAX_TEMPLATE_DISK_SIZE_MB,
        allow_null=True,
        default=None,
        help_text="系统盘（MB）。不填则不挂载独立系统盘，使用运行时默认的根文件系统；"
        "填写时为每个沙箱创建一块该大小的云盘作为系统盘，随沙箱销毁而删除",
    )
    env_vars = serializers.DictField(
        child=serializers.CharField(allow_blank=True), default=dict, help_text="沙箱的默认环境变量"
    )
    workdir = serializers.CharField(max_length=256, allow_blank=True, default="", help_text="工作目录，须为绝对路径")

    def validate_env_vars(self, value: dict[str, str]) -> dict[str, str]:
        if invalid := [k for k in value if not _ENV_VAR_NAME_RE.match(k)]:
            raise serializers.ValidationError(f"invalid environment variable names: {', '.join(sorted(invalid))}")
        return value

    def validate_workdir(self, value: str) -> str:
        if value and not value.startswith("/"):
            raise serializers.ValidationError("workdir must be an absolute path")
        return value


class E2BTemplateIDField(serializers.RegexField):
    """模板标识，即 SDK 创建沙箱时传入的 templateID"""

    def __init__(self, **kwargs):
        kwargs.setdefault("help_text", "模板标识，即 SDK 创建沙箱时传入的 templateID，创建后不可修改")
        kwargs.setdefault(
            "error_messages",
            {"invalid": "只能包含小写字母、数字和连接符(-)，以字母开头、字母或数字结尾，长度 2-31 个字符"},
        )
        super().__init__(TEMPLATE_ID_PATTERN, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        # 资源名按它切分出应用前缀与模板标识，内置模板也不能含有
        if CUSTOM_RESOURCE_NAME_SEPARATOR in value:
            raise serializers.ValidationError(f"不能包含 {CUSTOM_RESOURCE_NAME_SEPARATOR}")
        return value


class E2BBuiltinTemplateUpdateInputSLZ(E2BTemplateSpecInputSLZ):
    """修改内置模板，全量覆盖"""

    prewarm_count = serializers.IntegerField(min_value=0, default=0, help_text="每个集群预热的实例数")
    enabled = serializers.BooleanField(default=True, help_text="停用后不能再用它创建沙箱，已下发的 CR 保留")
    is_public = serializers.BooleanField(
        default=False, help_text="是否在开发者中心展示。不公开的模板仍可由任意应用按标识通过 SDK 使用"
    )


class E2BBuiltinTemplateCreateInputSLZ(E2BBuiltinTemplateUpdateInputSLZ):
    template_id = E2BTemplateIDField()
