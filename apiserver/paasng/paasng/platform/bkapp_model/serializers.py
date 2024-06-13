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

from typing import Any, Dict, List, Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from typing_extensions import TypeAlias

from paas_wl.bk_app.cnative.specs.constants import ScalingPolicy
from paas_wl.bk_app.processes.serializers import MetricSpecSLZ
from paas_wl.workloads.autoscaling.constants import DEFAULT_METRICS
from paasng.platform.applications.models import Application
from paasng.platform.modules.constants import DeployHookType


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
    """进程配置-环境相关配置"""

    environment_name = serializers.CharField(help_text="环境名称")

    plan_name = serializers.CharField(help_text="资源配额方案", required=False)
    target_replicas = serializers.IntegerField(help_text="副本数量(手动调节)", min_value=0, required=False)
    autoscaling = serializers.BooleanField(help_text="是否启用自动扩缩容", required=False, default=False)
    scaling_config = ScalingConfigSLZ(help_text="自动扩缩容配置", required=False, allow_null=True)


class ModuleProcessSpecMetadataSLZ(serializers.Serializer):
    """特性开关"""

    allow_multiple_image = serializers.BooleanField(default=False, help_text="是否允许使用多个不同镜像")


class ExecProbeActionSLZ(serializers.Serializer):
    command = serializers.ListField(help_text="探活命令", child=serializers.CharField(max_length=48), max_length=12)


class TcpSocketProbeActionSLZ(serializers.Serializer):
    port = serializers.IntegerField(help_text="探活端口", min_value=1, max_value=65535)
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)


class HTTPHeaderSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="标头名称")
    value = serializers.CharField(help_text="标头值")


class HttpGetProbeActionSLZ(serializers.Serializer):
    port = serializers.IntegerField(help_text="探活端口", min_value=1, max_value=65535)
    path = serializers.CharField(help_text="探活路径", max_length=128)
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)
    http_headers = serializers.ListField(help_text="HTTP 请求标头", required=False, child=HTTPHeaderSLZ())
    scheme = serializers.CharField(help_text="http/https", required=False)


class ProbeSLZ(serializers.Serializer):
    """探针配置"""

    exec = ExecProbeActionSLZ(help_text="exec 探活配置", required=False, allow_null=True)
    http_get = HttpGetProbeActionSLZ(help_text="http get 探活配置", required=False, allow_null=True)
    tcp_socket = TcpSocketProbeActionSLZ(help_text="tcp socket 探活配置", required=False, allow_null=True)
    initial_delay_seconds = serializers.IntegerField(help_text="初次探测延迟时间")
    timeout_seconds = serializers.IntegerField(help_text="探测超时时间")
    period_seconds = serializers.IntegerField(help_text="探测周期")
    success_threshold = serializers.IntegerField(help_text="成功阈值")
    failure_threshold = serializers.IntegerField(help_text="失败阈值")

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        probe_action_count = 0
        if attrs.get("exec"):
            probe_action_count += 1
        if attrs.get("httpGet"):
            probe_action_count += 1
        if attrs.get("tcpSocket"):
            probe_action_count += 1

        if probe_action_count > 1:
            raise serializers.ValidationError(_("至多设置一个探活配置"))
        if probe_action_count == 0:
            raise serializers.ValidationError(_("至少设置一个探活配置"))

        return attrs

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        attrs = super().to_internal_value(data)

        if attrs.get("http_get"):
            http_get_action = attrs.pop("http_get")
            if http_get_action.get("http_headers"):
                http_get_action["httpHeaders"] = http_get_action.pop("http_headers")
            attrs["httpGet"] = http_get_action

        if attrs.get("tcp_socket"):
            attrs["tcpSocket"] = attrs.pop("tcp_socket")

        attrs["initialDelaySeconds"] = attrs.pop("initial_delay_seconds")
        attrs["timeoutSeconds"] = attrs.pop("timeout_seconds")
        attrs["periodSeconds"] = attrs.pop("period_seconds")
        attrs["successThreshold"] = attrs.pop("success_threshold")
        attrs["failureThreshold"] = attrs.pop("failure_threshold")
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
    image_credential_name = serializers.CharField(help_text="镜像凭证", allow_null=True, required=False)
    command = serializers.ListSerializer(
        child=serializers.CharField(), help_text="启动命令", default=list, allow_null=True
    )
    args = serializers.ListSerializer(
        child=serializers.CharField(), help_text="命令参数", default=list, allow_null=True
    )
    port = serializers.IntegerField(
        help_text="容器端口", min_value=1, max_value=65535, allow_null=True, required=False
    )
    env_overlay = serializers.DictField(child=ProcessSpecEnvOverlaySLZ(), help_text="环境相关配置", required=False)
    probes = ProbeSetSLZ(help_text="容器探针配置", required=False, allow_null=True)


class ModuleProcessSpecsOutputSLZ(serializers.Serializer):
    proc_specs = ModuleProcessSpecSLZ(many=True, read_only=True)
    metadata = ModuleProcessSpecMetadataSLZ(read_only=True)


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

    bk_app_code = serializers.CharField(help_text="被服务发现的应用 code", max_length=20, source="bkAppCode")
    module_name = serializers.CharField(help_text="被服务发现的模块", max_length=20, source="moduleName", default=None)

    def validate(self, attrs):
        """校验应用和模块存在，否则抛出异常"""
        try:
            application = Application.objects.get(code=attrs["bkAppCode"])
        except Application.DoesNotExist:
            raise serializers.ValidationError(_("应用{}不存在").format(attrs["bkAppCode"]))

        # Check if module exists when the "module_name" is set
        if module_name := attrs["moduleName"]:  # noqa: SIM102
            if not application.modules.filter(name=module_name).exists():
                raise serializers.ValidationError(_("模块{}不存在").format(module_name))
        return attrs


BkSaaSList: TypeAlias = List[Dict[str, Optional[str]]]


class SvcDiscConfigSLZ(serializers.Serializer):
    bk_saas = serializers.ListField(help_text="服务发现列表", child=SvcDiscEntryBkSaaSSLZ())

    def validate_bk_saas(self, value: BkSaaSList) -> BkSaaSList:
        seen = set()
        for item in value:
            pair = (item["bkAppCode"], item["moduleName"] or "")
            if pair in seen:
                pair_for_display = f"AppID: {pair[0]}"
                if pair[1]:
                    pair_for_display += f", ModuleName: {pair[1]}"
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
