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

from typing import Any, Dict, List, Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from typing_extensions import TypeAlias

from paas_wl.bk_app.cnative.specs.constants import ScalingPolicy
from paas_wl.bk_app.processes.serializers import MetricSpecSLZ
from paas_wl.workloads.autoscaling.constants import DEFAULT_METRICS
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.constants import PORT_PLACEHOLDER, ExposedTypeName, NetworkProtocol
from paasng.platform.modules.constants import DeployHookType
from paasng.utils.dictx import get_items
from paasng.utils.serializers import IntegerOrCharField


class GetManifestInputSLZ(serializers.Serializer):
    output_format = serializers.ChoiceField(
        help_text="The output format", choices=["json", "yaml"], required=False, default="json"
    )


class ScalingConfigSLZ(serializers.Serializer):
    """扩缩容配置"""

    min_replicas = serializers.IntegerField(required=True, min_value=1, help_text="最小副本数")
    max_replicas = serializers.IntegerField(required=True, min_value=1, help_text="最大副本数")
    # WARNING: The metrics field is only for output and should never be saved to the database
    # TODO: Remove the metrics field when the UI does not reads it anymore.
    metrics = serializers.ListField(
        child=MetricSpecSLZ(), min_length=1, help_text="扩缩容指标", default=lambda: DEFAULT_METRICS
    )
    policy = serializers.ChoiceField(
        default=ScalingPolicy.DEFAULT, choices=ScalingPolicy.get_choices(), help_text="扩缩容策略"
    )


class ProcessSpecEnvOverlaySLZ(serializers.Serializer):
    """进程配置-单一环境相关配置"""

    plan_name = serializers.CharField(help_text="资源配额方案", required=False)
    target_replicas = serializers.IntegerField(help_text="副本数量(手动调节)", min_value=0, required=False)
    autoscaling = serializers.BooleanField(help_text="是否启用自动扩缩容", required=False, default=False)
    scaling_config = ScalingConfigSLZ(help_text="自动扩缩容配置", required=False, allow_null=True)


class ModuleProcessSpecMetadataSLZ(serializers.Serializer):
    """特性开关"""

    # TODO allow_multiple_image has been deprecated, remove it in the future
    allow_multiple_image = serializers.BooleanField(default=False, help_text="是否允许使用多个不同镜像")


class ExposedTypeSLZ(serializers.Serializer):
    name = serializers.ChoiceField(help_text="暴露服务的类型名", choices=ExposedTypeName.get_django_choices())


class ProcServiceSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="服务名称")
    target_port = IntegerOrCharField(help_text="目标容器端口")
    protocol = serializers.ChoiceField(
        help_text="协议", choices=NetworkProtocol.get_django_choices(), default=NetworkProtocol.TCP.value
    )
    exposed_type = ExposedTypeSLZ(help_text="暴露类型", required=False, allow_null=True)
    port = serializers.IntegerField(help_text="服务端口", min_value=1, max_value=65535, required=False)

    def validate_target_port(self, value):
        """validate whether target_port is a valid number or str '$PORT'"""
        try:
            target_port = int(value)
        except ValueError:
            if value != PORT_PLACEHOLDER:
                raise ValidationError(f"invalid target_port: {value}")
            return value

        if target_port < 1 or target_port > 65535:
            raise ValidationError(f"invalid target_port: {value}")

        return value


class ExecProbeActionSLZ(serializers.Serializer):
    command = serializers.ListField(help_text="探活命令", child=serializers.CharField(max_length=48), max_length=12)


class TCPSocketProbeActionSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="探活端口")
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)


class HTTPHeaderSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="标头名称")
    value = serializers.CharField(help_text="标头值")


class HTTPGetProbeActionSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="探活端口")
    path = serializers.CharField(help_text="探活路径", max_length=128)
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)
    http_headers = serializers.ListField(help_text="HTTP 请求标头", required=False, child=HTTPHeaderSLZ())
    scheme = serializers.CharField(help_text="http/https", required=False, default="HTTP")


class ProbeSLZ(serializers.Serializer):
    """探针配置"""

    exec = ExecProbeActionSLZ(help_text="exec 探活配置", required=False, allow_null=True)
    http_get = HTTPGetProbeActionSLZ(help_text="http get 探活配置", required=False, allow_null=True)
    tcp_socket = TCPSocketProbeActionSLZ(help_text="tcp socket 探活配置", required=False, allow_null=True)
    initial_delay_seconds = serializers.IntegerField(help_text="初次探测延迟时间", default=0)
    timeout_seconds = serializers.IntegerField(help_text="探测超时时间", default=1)
    period_seconds = serializers.IntegerField(help_text="探测周期", default=10)
    success_threshold = serializers.IntegerField(help_text="成功阈值", default=1)
    failure_threshold = serializers.IntegerField(help_text="失败阈值", default=3)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        probe_action_count = 0
        if attrs.get("exec"):
            probe_action_count += 1
        if attrs.get("http_get"):
            probe_action_count += 1
        if attrs.get("tcp_socket"):
            probe_action_count += 1

        if probe_action_count > 1:
            raise serializers.ValidationError(_("至多设置一个探活配置"))
        if probe_action_count == 0:
            raise serializers.ValidationError(_("至少设置一个探活配置"))

        return attrs


class ProbeSetSLZ(serializers.Serializer):
    """探针集合"""

    liveness = ProbeSLZ(help_text="存活探针", required=False, allow_null=True)
    readiness = ProbeSLZ(help_text="就绪探针", required=False, allow_null=True)
    startup = ProbeSLZ(help_text="启动探针", required=False, allow_null=True)


class ModuleProcessSpecSLZ(serializers.Serializer):
    """进程配置"""

    name = serializers.CharField(help_text="进程名称")

    image = serializers.CharField(help_text="镜像仓库/镜像地址", allow_null=True, required=False)
    command = serializers.ListSerializer(
        child=serializers.CharField(), help_text="启动命令", default=list, allow_null=True
    )
    args = serializers.ListSerializer(
        child=serializers.CharField(), help_text="命令参数", default=list, allow_null=True
    )
    services = serializers.ListSerializer(
        child=ProcServiceSLZ(), help_text="进程服务列表", allow_null=True, required=False
    )
    port = serializers.IntegerField(
        help_text="容器端口", min_value=1, max_value=65535, allow_null=True, required=False
    )
    env_overlay = serializers.DictField(child=ProcessSpecEnvOverlaySLZ(), help_text="环境相关配置", required=False)
    probes = ProbeSetSLZ(help_text="容器探针配置", required=False, allow_null=True)

    def validate_services(self, value):
        """check whether name, target_port or port are duplicated"""
        if not value:
            return value

        names = set()
        target_ports = set()
        ports = set()

        for svc in value:
            name = svc["name"]
            if name in names:
                raise ValidationError(f"duplicate service name: {name}")
            names.add(name)

            target_port = svc["target_port"]
            if target_port in target_ports:
                raise ValidationError(f"duplicate target_port: {target_port}")
            target_ports.add(target_port)

            port = svc.get("port")
            if port:
                if port in ports:
                    raise ValidationError(f"duplicate port: {port}")
                ports.add(port)

        return value


class ModuleProcessSpecsOutputSLZ(serializers.Serializer):
    proc_specs = ModuleProcessSpecSLZ(many=True, read_only=True)
    metadata = ModuleProcessSpecMetadataSLZ(read_only=True)


class ModuleProcessSpecsInputSLZ(serializers.Serializer):
    proc_specs = serializers.ListField(child=ModuleProcessSpecSLZ(), min_length=1)

    def validate(self, data):
        data = super().validate(data)
        self._validate_exposed_types(data["proc_specs"])
        return data

    def _validate_exposed_types(self, proc_specs):
        """check whether exposed_types are duplicated.
        说明: 一个 BkApp 只能有一个 bk/http 类型的暴露服务作为主入口
        """
        exposed_types = set()

        for proc in proc_specs:
            proc_services = proc.get("services")

            if not proc_services:
                continue

            for svc in proc_services:
                exposed_type_name = get_items(svc, ["exposed_type", "name"])

                if not exposed_type_name:
                    continue

                if exposed_type_name in exposed_types:
                    raise ValidationError(f"exposed_type {exposed_type_name} is duplicated in one app module")

                exposed_types.add(exposed_type_name)


class ModuleDeployHookSLZ(serializers.Serializer):
    """钩子命令"""

    type = serializers.ChoiceField(help_text="钩子类型", choices=DeployHookType.get_choices())

    proc_command = serializers.CharField(
        help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一",
        required=False,
        allow_null=True,
    )
    command = serializers.ListSerializer(child=serializers.CharField(), help_text="启动命令", default=list)
    args = serializers.ListSerializer(child=serializers.CharField(), help_text="命令参数", default=list)
    enabled = serializers.BooleanField(allow_null=True, default=False)


class SvcDiscEntryBkSaaSSLZ(serializers.Serializer):
    """A service discovery entry that represents an application and an optional module."""

    bk_app_code = serializers.CharField(help_text="被服务发现的应用 code", max_length=20)
    module_name = serializers.CharField(help_text="被服务发现的模块", max_length=20, default=None)

    def to_internal_value(self, data):
        # Note: 兼容只传递 app-code 的格式(app_desc.yaml spec_version:2)
        if isinstance(data, str):
            data = {"bk_app_code": data}
        return super().to_internal_value(data)

    def validate(self, attrs):
        """校验应用和模块存在，否则抛出异常"""
        try:
            application = Application.objects.get(code=attrs["bk_app_code"])
        except Application.DoesNotExist:
            raise serializers.ValidationError(_("应用{}不存在").format(attrs["bk_app_code"]))

        # Check if module exists when the "module_name" is set
        if module_name := attrs["module_name"]:  # noqa: SIM102
            if not application.modules.filter(name=module_name).exists():
                raise serializers.ValidationError(_("模块{}不存在").format(module_name))
        return attrs


BkSaaSList: TypeAlias = List[Dict[str, Optional[str]]]


class SvcDiscConfigSLZ(serializers.Serializer):
    bk_saas = serializers.ListField(help_text="服务发现列表", child=SvcDiscEntryBkSaaSSLZ())

    def validate_bk_saas(self, value: BkSaaSList) -> BkSaaSList:
        seen = set()
        for item in value:
            pair = (item["bk_app_code"], item["module_name"] or "")
            if pair in seen:
                pair_for_display = f"AppID: {pair[0]}"
                if pair[1]:
                    pair_for_display += f", module_name: {pair[1]}"
                raise serializers.ValidationError(_("服务发现列表中存在重复项：{}").format(f"[{pair_for_display}]"))
            seen.add(pair)
        return value


class HostAliasSLZ(serializers.Serializer):
    ip = serializers.IPAddressField(help_text="ip")
    hostnames = serializers.ListField(help_text="域名列表", child=serializers.CharField())


class DomainResolutionSLZ(serializers.Serializer):
    nameservers = serializers.ListField(help_text="DNS 服务器", child=serializers.IPAddressField(), required=False)
    host_aliases = serializers.ListField(help_text="域名解析列表", child=HostAliasSLZ(), required=False)

    def validate(self, data):
        nameservers = data.get("nameservers")
        host_aliases = data.get("host_aliases")

        if (nameservers is None) and (host_aliases is None):
            raise serializers.ValidationError(_("至少需要提供一个有效值：nameservers 或 host_aliases"))

        return data


class BkAppModelSLZ(serializers.Serializer):
    manifest = serializers.JSONField(label=_("BkApp 配置信息"))
