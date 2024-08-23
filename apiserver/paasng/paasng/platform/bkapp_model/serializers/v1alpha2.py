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

from typing import List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.bkapp_model.constants import ImagePullPolicy, NetworkProtocol, ResQuotaPlan, ScalingPolicy
from paasng.platform.bkapp_model.entities import (
    Addon,
    AppBuildConfig,
    AutoscalingOverlay,
    DomainResolution,
    EnvVar,
    EnvVarOverlay,
    Hooks,
    Mount,
    MountOverlay,
    Process,
    ReplicasOverlay,
    ResQuotaOverlay,
    SvcDiscConfig,
    v1alpha2,
)
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.serializers import IntegerOrCharField, field_env_var_key
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH, PROC_TYPE_PATTERN

from .serializers import ExecProbeActionSLZ, ExposedTypeSLZ, HTTPHeaderSLZ, TCPSocketProbeActionSLZ


class BaseEnvVarFields(serializers.Serializer):
    """Base fields for validating EnvVar."""

    name = field_env_var_key()
    value = serializers.CharField(allow_blank=False)


class EnvVarInputSLZ(BaseEnvVarFields):
    def to_internal_value(self, data) -> EnvVar:
        d = super().to_internal_value(data)
        return EnvVar(**d)


class EnvVarOverlayInputSLZ(BaseEnvVarFields):
    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")

    def to_internal_value(self, data) -> EnvVarOverlay:
        d = super().to_internal_value(data)
        return EnvVarOverlay(**d)


class AddonSpecInputSLZ(serializers.Serializer):
    """Validate the items in the `addons.specs` field."""

    name = serializers.CharField(required=True)
    value = serializers.CharField(required=True)


class AddonInputSLZ(serializers.Serializer):
    """Validate the items in the `addons` field."""

    name = serializers.CharField(required=True)
    specs = serializers.ListField(child=AddonSpecInputSLZ(), default=None)
    sharedFromModule = serializers.CharField(default=None, source="shared_from_module")

    def to_internal_value(self, data) -> Addon:
        d = super().to_internal_value(data)
        return Addon(**d)


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
    """Validate the `mounts` field's item."""

    def to_internal_value(self, data) -> Mount:
        d = super().to_internal_value(data)
        return Mount(**d)


class MountOverlayInputSLZ(BaseMountFields):
    """Validate the `mounts` field in envOverlay."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")

    def to_internal_value(self, data) -> MountOverlay:
        d = super().to_internal_value(data)
        return MountOverlay(**d)


class ReplicasOverlayInputSLZ(serializers.Serializer):
    """Validate the `replicas` field in envOverlay."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")
    process = serializers.CharField()
    count = serializers.IntegerField()

    def to_internal_value(self, data) -> ReplicasOverlay:
        d = super().to_internal_value(data)
        return ReplicasOverlay(**d)


class ResQuotaOverlayInputSLZ(serializers.Serializer):
    """Validate the `resQuotas` field in envOverlay"""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")
    process = serializers.CharField()
    plan = serializers.ChoiceField(choices=ResQuotaPlan.get_choices(), allow_null=True, default=None)

    def to_internal_value(self, data) -> ResQuotaOverlay:
        d = super().to_internal_value(data)
        return ResQuotaOverlay(**d)


class AutoscalingSpecInputSLZ(serializers.Serializer):
    """Base fields for validating AutoscalingSpec."""

    minReplicas = serializers.IntegerField(required=True, min_value=1, source="min_replicas")
    maxReplicas = serializers.IntegerField(required=True, min_value=1, source="max_replicas")
    policy = serializers.ChoiceField(default=ScalingPolicy.DEFAULT, choices=ScalingPolicy.get_choices())


class AutoscalingOverlayInputSLZ(AutoscalingSpecInputSLZ):
    """Validate the `autoscaling` field in envOverlay"""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices(), source="env_name")
    process = serializers.CharField()

    def to_internal_value(self, data) -> AutoscalingOverlay:
        d = super().to_internal_value(data)
        return AutoscalingOverlay(**d)


class EnvOverlayInputSLZ(serializers.Serializer):
    """Validate the `envOverlay` field."""

    replicas = serializers.ListField(child=ReplicasOverlayInputSLZ(), required=False)
    resQuotas = serializers.ListField(child=ResQuotaOverlayInputSLZ(), required=False, source="res_quotas")
    envVariables = serializers.ListField(child=EnvVarOverlayInputSLZ(), required=False, source="env_variables")
    autoscaling = serializers.ListField(child=AutoscalingOverlayInputSLZ(), required=False)
    mounts = serializers.ListField(child=MountOverlayInputSLZ(), required=False)


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

    def to_internal_value(self, data) -> AppBuildConfig:
        d = super().to_internal_value(data)
        return AppBuildConfig(**d)


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
    name = serializers.CharField()
    targetPort = serializers.IntegerField(min_value=1, max_value=65535, source="target_port")
    protocol = serializers.ChoiceField(choices=NetworkProtocol.get_django_choices(), default=NetworkProtocol.TCP.value)
    exposedType = ExposedTypeSLZ(allow_null=True, default=None, source="exposed_type")
    port = serializers.IntegerField(min_value=1, max_value=65535, allow_null=True, default=None)


class ProcessInputSLZ(serializers.Serializer):
    """Validate the `processes` field."""

    name = serializers.RegexField(regex=PROC_TYPE_PATTERN, max_length=PROC_TYPE_MAX_LENGTH)
    replicas = serializers.IntegerField(min_value=0, allow_null=True, default=None)
    resQuotaPlan = serializers.ChoiceField(
        choices=ResQuotaPlan.get_choices(), allow_null=True, default=None, source="res_quota_plan"
    )
    targetPort = serializers.IntegerField(
        min_value=1, max_value=65535, allow_null=True, default=None, source="target_port"
    )
    command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    procCommand = serializers.CharField(allow_null=True, required=False, source="proc_command")
    autoscaling = AutoscalingSpecInputSLZ(allow_null=True, default=None)
    probes = ProbeSetInputSLZ(allow_null=True, default=None)
    services = serializers.ListField(child=ProcServiceInputSLZ(), allow_null=True, default=None)


class HooksInputSLZ(serializers.Serializer):
    """Validate the `hooks` field."""

    class HookInputSLZ(serializers.Serializer):
        command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
        args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
        procCommand = serializers.CharField(allow_null=True, required=False, source="proc_command")

    preRelease = HookInputSLZ(allow_null=True, default=None, source="pre_release")

    def to_internal_value(self, data) -> Hooks:
        d = super().to_internal_value(data)
        return Hooks(**d)


class BkSaaSInputSLZ(serializers.Serializer):
    """Validate the `bkSaaS` field."""

    bkAppCode = serializers.CharField(source="bk_app_code")
    moduleName = serializers.CharField(required=False, allow_null=True, source="module_name")


class ServiceDiscoveryInputSLZ(serializers.Serializer):
    """Validate the `serviceDiscovery` field."""

    bkSaaS = serializers.ListField(child=BkSaaSInputSLZ(), required=False, allow_empty=True, source="bk_saas")

    def to_internal_value(self, data) -> SvcDiscConfig:
        d = super().to_internal_value(data)
        return SvcDiscConfig(**d)


class HostAliasSLZ(serializers.Serializer):
    ip = serializers.IPAddressField()
    hostnames = serializers.ListField(child=serializers.CharField())


class DomainResolutionInputSLZ(serializers.Serializer):
    nameservers = serializers.ListField(child=serializers.IPAddressField(), required=False)
    hostAliases = serializers.ListField(child=HostAliasSLZ(), required=False, source="host_aliases")

    def to_internal_value(self, data) -> DomainResolution:
        d = super().to_internal_value(data)
        return DomainResolution(**d)


class BkAppSpecInputSLZ(serializers.Serializer):
    """BkApp resource slz in camel-case format"""

    build = BuildInputSLZ(allow_null=True, default=None)
    processes = serializers.ListField(child=ProcessInputSLZ())
    configuration = ConfigurationInputSLZ(required=False)
    addons = serializers.ListField(child=AddonInputSLZ(), required=False, allow_empty=True)
    mounts = serializers.ListField(child=MountInputSLZ(), required=False, allow_empty=True)
    hooks = HooksInputSLZ(allow_null=True, default=None)
    envOverlay = EnvOverlayInputSLZ(required=False, source="env_overlay")
    svcDiscovery = ServiceDiscoveryInputSLZ(required=False, source="svc_discovery")
    domainResolution = DomainResolutionInputSLZ(required=False, source="domain_resolution")

    def to_internal_value(self, data) -> v1alpha2.BkAppSpec:
        d = super().to_internal_value(data)
        return v1alpha2.BkAppSpec(**d)

    def validate(self, data: v1alpha2.BkAppSpec):
        self._validate_proc_services(data.processes)
        return data

    def _validate_proc_services(self, processes: List[Process]):
        """validate process services by two rules as below:
        - check whether service name, targetPort or port are duplicated in one process
        - check whether exposedTypes are duplicated in one module
        """
        exposed_types = set()

        for proc in processes:
            names = set()
            target_ports = set()
            ports = set()

            for svc in proc.services or []:
                name = svc.name
                if name in names:
                    raise ValidationError(f"duplicate service name: {name}")
                names.add(name)

                target_port = svc.target_port
                if target_port in target_ports:
                    raise ValidationError(f"duplicate targetPort: {target_port}")
                target_ports.add(target_port)

                port = svc.port
                if port:
                    if port in ports:
                        raise ValidationError(f"duplicate port: {port}")
                    ports.add(port)

                exposed_type = svc.exposed_type
                if exposed_type:
                    if exposed_type.name in exposed_types:
                        raise ValidationError(f"duplicate exposedType: {exposed_type.name}")
                    exposed_types.add(exposed_type.name)
