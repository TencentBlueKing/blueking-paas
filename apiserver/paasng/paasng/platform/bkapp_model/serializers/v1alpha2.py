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

from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.utils.camel_converter import camel_to_snake_case
from paasng.accessories.proc_components.exceptions import ComponentNotFound, ComponentPropertiesInvalid
from paasng.accessories.proc_components.manager import validate_component_properties
from paasng.platform.bkapp_model.constants import (
    PORT_PLACEHOLDER,
    ImagePullPolicy,
    NetworkProtocol,
    ResQuotaPlan,
    ScalingPolicy,
)
from paasng.platform.bkapp_model.entities import Process, v1alpha2
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.serializers import IntegerOrCharField, field_env_var_key
from paasng.utils.structure import NOTSET
from paasng.utils.validators import (
    DNS_MAX_LENGTH,
    DNS_SAFE_PATTERN,
    PROC_TYPE_MAX_LENGTH,
    PROC_TYPE_PATTERN,
)

from .serializers import ExecProbeActionSLZ, ExposedTypeSLZ, HTTPHeaderSLZ, TCPSocketProbeActionSLZ


class BaseEnvVarFields(serializers.Serializer):
    """Base fields for validating EnvVar."""

    name = field_env_var_key()
    value = serializers.CharField(allow_blank=True)
    description = serializers.CharField(
        allow_null=True,
        max_length=200,
        default="",
        help_text="变量描述, 不超过 200 个字符",
    )


class EnvVarInputSLZ(BaseEnvVarFields):
    """EnvVarInputSLZ validate the items in the `env` field."""


class EnvVarOverlayInputSLZ(BaseEnvVarFields):
    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")


class AddonSpecInputSLZ(serializers.Serializer):
    """Validate the items in the `addons.specs` field."""

    name = serializers.CharField(required=True)
    value = serializers.CharField(required=True)


class AddonInputSLZ(serializers.Serializer):
    """Validate the items in the `addons` field."""

    name = serializers.CharField(required=True)
    specs = serializers.ListField(child=AddonSpecInputSLZ(), default=None)
    sharedFromModule = serializers.CharField(default=None, source="shared_from_module")


class BaseMountFields(serializers.Serializer):
    """Base fields for validating Mount."""

    class SourceInputSLZ(serializers.Serializer):
        class ConfigMapInputSLZ(serializers.Serializer):
            name = serializers.CharField()

        configMap = ConfigMapInputSLZ(source="config_map")

    name = serializers.RegexField(regex=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63)
    mountPath = serializers.RegexField(regex=r"^/([^/\0]+(/)?)*$", source="mount_path")
    source = SourceInputSLZ()


class MountInputSLZ(BaseMountFields):
    """MountInputSLZ validate the items in the `mounts` field."""


class MountOverlayInputSLZ(BaseMountFields):
    """MountOverlayInputSLZ validate the items in the `envOverlay.mounts` field."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")


class ReplicasOverlayInputSLZ(serializers.Serializer):
    """ReplicasOverlayInputSLZ validate the items in the `envOverlay.replicas` field."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")
    process = serializers.CharField()
    count = serializers.IntegerField()


class ResQuotaOverlayInputSLZ(serializers.Serializer):
    """ResQuotaOverlayInputSLZ validate the items in the `envOverlay.resQuotas` field."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")
    process = serializers.CharField()
    plan = serializers.ChoiceField(choices=ResQuotaPlan.get_choices(), allow_null=True, default=None)


class AutoscalingSpecInputSLZ(serializers.Serializer):
    """Base fields for validating AutoscalingSpec."""

    minReplicas = serializers.IntegerField(required=True, min_value=1, source="min_replicas")
    maxReplicas = serializers.IntegerField(required=True, min_value=1, source="max_replicas")
    policy = serializers.ChoiceField(default=ScalingPolicy.DEFAULT, choices=ScalingPolicy.get_choices())


class AutoscalingOverlayInputSLZ(AutoscalingSpecInputSLZ):
    """Validate the `autoscaling` field in envOverlay"""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")
    process = serializers.CharField()


class EnvOverlayInputSLZ(serializers.Serializer):
    """Validate the `envOverlay` field."""

    replicas = serializers.ListField(child=ReplicasOverlayInputSLZ(), default=NOTSET)
    resQuotas = serializers.ListField(child=ResQuotaOverlayInputSLZ(), default=NOTSET, source="res_quotas")
    envVariables = serializers.ListField(child=EnvVarOverlayInputSLZ(), default=NOTSET, source="env_variables")
    autoscaling = serializers.ListField(child=AutoscalingOverlayInputSLZ(), default=NOTSET)
    mounts = serializers.ListField(child=MountOverlayInputSLZ(), default=NOTSET)


class ConfigurationInputSLZ(serializers.Serializer):
    """Validate the `configuration` field."""

    env = serializers.ListField(child=EnvVarInputSLZ())


class BuildInputSLZ(serializers.Serializer):
    """Validate the `build` field."""

    image = serializers.CharField(allow_null=True, default=None, allow_blank=True)
    imagePullPolicy = serializers.ChoiceField(
        choices=ImagePullPolicy.get_choices(), default=ImagePullPolicy.IF_NOT_PRESENT, source="image_pull_policy"
    )
    imageCredentialsName = serializers.CharField(
        allow_null=True, default=None, allow_blank=True, source="image_credentials_name"
    )


class HTTPGetActionInputSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="探活端口")
    path = serializers.CharField(help_text="探活路径", max_length=128)
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)
    httpHeaders = serializers.ListField(
        help_text="HTTP 请求标头", required=False, child=HTTPHeaderSLZ(), source="http_headers"
    )
    scheme = serializers.CharField(help_text="http/https", required=False, default="HTTP")


class ProbeInputSLZ(serializers.Serializer):
    """探针配置"""

    exec = ExecProbeActionSLZ(help_text="exec 探活配置", required=False, allow_null=True)
    httpGet = HTTPGetActionInputSLZ(help_text="http get 探活配置", required=False, allow_null=True, source="http_get")
    tcpSocket = TCPSocketProbeActionSLZ(
        help_text="tcp socket 探活配置", required=False, allow_null=True, source="tcp_socket"
    )
    initialDelaySeconds = serializers.IntegerField(
        help_text="初次探测延迟时间", source="initial_delay_seconds", default=0
    )
    timeoutSeconds = serializers.IntegerField(help_text="探测超时时间", source="timeout_seconds", default=1)
    periodSeconds = serializers.IntegerField(help_text="探测周期", source="period_seconds", default=10)
    successThreshold = serializers.IntegerField(help_text="成功阈值", source="success_threshold", default=1)
    failureThreshold = serializers.IntegerField(help_text="失败阈值", source="failure_threshold", default=3)


class ProbeSetInputSLZ(serializers.Serializer):
    """探针集合"""

    liveness = ProbeInputSLZ(help_text="存活探针", required=False, allow_null=True)
    readiness = ProbeInputSLZ(help_text="就绪探针", required=False, allow_null=True)
    startup = ProbeInputSLZ(help_text="启动探针", required=False, allow_null=True)


class ProcServiceInputSLZ(serializers.Serializer):
    name = serializers.RegexField(
        regex=DNS_SAFE_PATTERN,
        max_length=DNS_MAX_LENGTH,
        error_messages={
            "invalid": _(
                '服务名应仅包含小写字母，数字字符和连字符"-"，且必须以字母数字字符开头和结尾，最大长度不超过 63'
            )
        },
    )
    targetPort = IntegerOrCharField(source="target_port")
    protocol = serializers.ChoiceField(choices=NetworkProtocol.get_django_choices(), default=NetworkProtocol.TCP.value)
    exposedType = ExposedTypeSLZ(allow_null=True, default=None, source="exposed_type")
    port = serializers.IntegerField(min_value=1, max_value=65535, allow_null=True, default=None)

    def validate_targetPort(self, value):  # noqa: N802
        """validate whether targetPort is a valid number or str '$PORT'"""
        try:
            target_port = int(value)
        except ValueError:
            if value != PORT_PLACEHOLDER:
                raise serializers.ValidationError(f"Invalid targetPort: {value}")
            return value

        if target_port < 1 or target_port > 65535:
            raise serializers.ValidationError(f"Invalid targetPort: {value}")

        return value


class ComponentInputSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="组件类型", max_length=32)
    version = serializers.CharField(help_text="组件版本", max_length=32)
    properties = serializers.DictField(help_text="组件参数", required=False)

    def to_internal_value(self, data: Dict) -> Dict:
        internal_value = super().to_internal_value(data)
        # 检查是否存在properties字段
        if "properties" in data:
            # 转换 properties 中的键名
            internal_value["properties"] = camel_to_snake_case(data["properties"])

        return internal_value

    def validate(self, attrs: Dict) -> Dict:
        try:
            validate_component_properties(attrs["name"], attrs["version"], attrs.get("properties", {}))
        except ComponentNotFound:
            raise ValidationError(_("组件 {}-{} 不存在").format(attrs["name"], attrs["version"]))
        except ComponentPropertiesInvalid as e:
            raise ValidationError(_("参数校验失败")) from e

        return attrs


class ProcessInputSLZ(serializers.Serializer):
    """Validate the `processes` field."""

    name = serializers.RegexField(regex=PROC_TYPE_PATTERN, max_length=PROC_TYPE_MAX_LENGTH)
    replicas = serializers.IntegerField(min_value=0, allow_null=True, default=NOTSET)
    resQuotaPlan = serializers.ChoiceField(
        choices=ResQuotaPlan.get_choices(), allow_null=True, default=None, source="res_quota_plan"
    )
    targetPort = serializers.IntegerField(
        min_value=1,
        max_value=65535,
        allow_null=True,
        default=None,
        source="target_port",
        help_text="[deprecated] 容器端口",
    )
    command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    procCommand = serializers.CharField(allow_null=True, required=False, source="proc_command")
    autoscaling = AutoscalingSpecInputSLZ(allow_null=True, default=NOTSET)
    probes = ProbeSetInputSLZ(allow_null=True, default=None)
    services = serializers.ListField(child=ProcServiceInputSLZ(), allow_null=True, default=None)
    components = serializers.ListField(child=ComponentInputSLZ(), allow_null=True, default=None)


class HooksInputSLZ(serializers.Serializer):
    """Validate the `hooks` field."""

    class HookInputSLZ(serializers.Serializer):
        command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
        args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
        procCommand = serializers.CharField(allow_null=True, required=False, source="proc_command")

    preRelease = HookInputSLZ(allow_null=True, default=None, source="pre_release")


class BkSaaSInputSLZ(serializers.Serializer):
    """Validate the `bkSaaS` field."""

    bkAppCode = serializers.CharField(source="bk_app_code")
    moduleName = serializers.CharField(required=False, allow_null=True, source="module_name")


class ServiceDiscoveryInputSLZ(serializers.Serializer):
    """ServiceDiscoveryInputSLZ"""

    bkSaaS = serializers.ListField(child=BkSaaSInputSLZ(), required=False, allow_empty=True, source="bk_saas")


class HostAliasSLZ(serializers.Serializer):
    ip = serializers.IPAddressField()
    hostnames = serializers.ListField(child=serializers.CharField())


class DomainResolutionInputSLZ(serializers.Serializer):
    nameservers = serializers.ListField(child=serializers.IPAddressField(), required=False)
    hostAliases = serializers.ListField(child=HostAliasSLZ(), required=False, source="host_aliases")


class MetricInputSLZ(serializers.Serializer):
    process = serializers.CharField(help_text="进程名称")
    serviceName = serializers.CharField(help_text="服务端口名称", source="service_name")
    path = serializers.CharField(help_text="采集 metric 数据的 http url 路径", default="/metrics")
    params = serializers.DictField(help_text="采集 metric 数据的 http url 路径参数", required=False, allow_null=True)


class MonitoringInputSLZ(serializers.Serializer):
    metrics = serializers.ListSerializer(child=MetricInputSLZ(), required=False, allow_null=True)


class ObservabilityInputSLZ(serializers.Serializer):
    monitoring = MonitoringInputSLZ(required=False, allow_null=True)


class BkAppSpecInputSLZ(serializers.Serializer):
    """BkApp resource slz in camel-case format"""

    build = BuildInputSLZ(allow_null=True, default=None)
    processes = serializers.ListField(child=ProcessInputSLZ(), allow_empty=False)
    configuration = ConfigurationInputSLZ(required=False)
    addons = serializers.ListField(child=AddonInputSLZ(), required=False, allow_empty=True)
    mounts = serializers.ListField(child=MountInputSLZ(), required=False, allow_empty=True)
    hooks = HooksInputSLZ(allow_null=True, default=NOTSET)
    envOverlay = EnvOverlayInputSLZ(source="env_overlay", default=NOTSET)
    svcDiscovery = ServiceDiscoveryInputSLZ(source="svc_discovery", default=NOTSET)
    domainResolution = DomainResolutionInputSLZ(source="domain_resolution", default=NOTSET)
    observability = ObservabilityInputSLZ(required=False)

    def to_internal_value(self, data) -> v1alpha2.BkAppSpec:
        d = super().to_internal_value(data)
        return v1alpha2.BkAppSpec(**d)

    def validate(self, data: v1alpha2.BkAppSpec):
        self._validate_proc_services(data.processes)
        self._validate_observability(data)
        return data

    def _validate_proc_services(self, processes: List[Process]):
        """validate process services by two rules as below:
        - check whether service name, targetPort or port are duplicated in one process
        - check whether exposedTypes are duplicated in one module
        - check whether multiple exposedTypes in one module
        """
        exposed_types = set()

        for proc in processes:
            names = set()
            target_ports = set()
            ports = set()

            for svc in proc.services or []:
                name = svc.name
                if name in names:
                    raise ValidationError(f"process({proc.name}) has duplicate service name: {name}")
                names.add(name)

                target_port = svc.target_port
                if target_port in target_ports:
                    raise ValidationError(f"process({proc.name}) has duplicate targetPort: {target_port}")
                target_ports.add(target_port)

                port = svc.port
                if port:
                    if port in ports:
                        raise ValidationError(f"process({proc.name}) has duplicate port: {port}")
                    ports.add(port)

                exposed_type = svc.exposed_type
                if exposed_type:
                    if exposed_type.name in exposed_types:
                        raise ValidationError(f"duplicate exposedType: {exposed_type.name}")
                    exposed_types.add(exposed_type.name)

        if len(exposed_types) > 1:
            raise ValidationError("setting multiple exposedTypes in an app module is not supported")

    def _validate_observability(self, data: v1alpha2.BkAppSpec):
        """validate observability config by rules as below:
        - check whether metric match any process and its services
        """
        if not data.observability or not data.observability.monitoring:
            return

        metrics = data.observability.monitoring.metrics
        if not metrics:
            return

        process_map = {proc.name: proc for proc in data.processes}

        for metric in metrics:
            process = process_map.get(metric.process)

            if not process:
                raise ValidationError(f"metric process({metric.process}) not match any process")

            if metric.service_name not in [svc.name for svc in process.services or []]:
                raise ValidationError(
                    f"metric serviceName({metric.service_name}) not match any service in process({metric.process})"
                )
