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

from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan, ScalingPolicy
from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.platform.engine.constants import AppEnvName, ImagePullPolicy
from paasng.utils.serializers import IntegerOrCharField, field_env_var_key
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH, PROC_TYPE_PATTERN


class BaseEnvVarFields(serializers.Serializer):
    """Base fields for validating EnvVar."""

    name = field_env_var_key()
    value = serializers.CharField(allow_blank=False)


class EnvVarInputSLZ(BaseEnvVarFields):
    def to_internal_value(self, data) -> bk_app.EnvVar:
        # NOTE: Should we define another "EnvVar" type instead of importing from the crd module?
        d = super().to_internal_value(data)
        return bk_app.EnvVar(**d)


class EnvVarOverlayInputSLZ(BaseEnvVarFields):
    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())

    def to_internal_value(self, data) -> bk_app.EnvVarOverlay:
        d = super().to_internal_value(data)
        return bk_app.EnvVarOverlay(**d)


class AddonSpecInputSLZ(serializers.Serializer):
    """Validate the items in the `addons.specs` field."""

    name = serializers.CharField(required=True)
    value = serializers.CharField(required=True)


class AddonInputSLZ(serializers.Serializer):
    """Validate the items in the `addons` field."""

    name = serializers.CharField(required=True)
    specs = serializers.ListField(child=AddonSpecInputSLZ(), default=None)
    sharedFromModule = serializers.CharField(default=None)


class BaseMountFields(serializers.Serializer):
    """Base fields for validating Mount."""

    class SourceInputSLZ(serializers.Serializer):
        class ConfigMapInputSLZ(serializers.Serializer):
            name = serializers.CharField()

        configMap = ConfigMapInputSLZ()

    name = serializers.RegexField(regex=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63)
    mountPath = serializers.RegexField(regex=r"^/([^/\0]+(/)?)*$")
    source = SourceInputSLZ()


class MountInputSLZ(BaseMountFields):
    """Validate the `mounts` field's item."""

    def to_internal_value(self, data) -> bk_app.Mount:
        d = super().to_internal_value(data)
        return bk_app.Mount(**d)


class MountOverlayInputSLZ(BaseMountFields):
    """Validate the `mounts` field in envOverlay."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())

    def to_internal_value(self, data) -> bk_app.MountOverlay:
        d = super().to_internal_value(data)
        return bk_app.MountOverlay(**d)


class ReplicasOverlayInputSLZ(serializers.Serializer):
    """Validate the `replicas` field in envOverlay."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())
    process = serializers.CharField()
    count = serializers.IntegerField()

    def to_internal_value(self, data) -> bk_app.ReplicasOverlay:
        d = super().to_internal_value(data)
        return bk_app.ReplicasOverlay(**d)


class ResQuotaOverlayInputSLZ(serializers.Serializer):
    """Validate the `resQuotas` field in envOverlay"""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())
    process = serializers.CharField()
    plan = serializers.ChoiceField(choices=ResQuotaPlan.get_choices(), allow_null=True, default=None)

    def to_internal_value(self, data) -> bk_app.ResQuotaOverlay:
        d = super().to_internal_value(data)
        return bk_app.ResQuotaOverlay(**d)


class AutoscalingSpecInputSLZ(serializers.Serializer):
    """Base fields for validating AutoscalingSpec."""

    minReplicas = serializers.IntegerField(required=True, min_value=1)
    maxReplicas = serializers.IntegerField(required=True, min_value=1)
    policy = serializers.ChoiceField(default=ScalingPolicy.DEFAULT, choices=ScalingPolicy.get_choices())


class AutoscalingOverlayInputSLZ(AutoscalingSpecInputSLZ):
    """Validate the `autoscaling` field in envOverlay"""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())
    process = serializers.CharField()

    def to_internal_value(self, data) -> bk_app.AutoscalingOverlay:
        d = super().to_internal_value(data)
        return bk_app.AutoscalingOverlay(**d)


class EnvOverlayInputSLZ(serializers.Serializer):
    """Validate the `envOverlay` field."""

    replicas = serializers.ListField(child=ReplicasOverlayInputSLZ(), required=False)
    resQuotas = serializers.ListField(child=ResQuotaOverlayInputSLZ(), required=False)
    envVariables = serializers.ListField(child=EnvVarOverlayInputSLZ(), required=False)
    autoscaling = serializers.ListField(child=AutoscalingOverlayInputSLZ(), required=False)
    mounts = serializers.ListField(child=MountOverlayInputSLZ(), required=False)


class ConfigurationInputSLZ(serializers.Serializer):
    """Validate the `configuration` field."""

    env = serializers.ListField(child=EnvVarInputSLZ())


class BuildInputSLZ(serializers.Serializer):
    """Validate the `build` field."""

    image = serializers.CharField(allow_null=True, default=None, allow_blank=True)
    imagePullPolicy = serializers.ChoiceField(
        choices=ImagePullPolicy.get_choices(), default=ImagePullPolicy.IF_NOT_PRESENT
    )
    imageCredentialsName = serializers.CharField(allow_null=True, default=None, allow_blank=True)

    def to_internal_value(self, data) -> bk_app.BkAppBuildConfig:
        d = super().to_internal_value(data)
        return bk_app.BkAppBuildConfig(**d)


class ExecActionInputSLZ(serializers.Serializer):
    command = serializers.ListField(help_text="探活命令", child=serializers.CharField(max_length=48), max_length=12)

    def to_internal_value(self, data) -> bk_app.ExecAction:
        d = super().to_internal_value(data)
        return bk_app.ExecAction(**d)


class TCPSocketActionInputSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="探活端口")
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)

    def to_internal_value(self, data) -> bk_app.TCPSocketAction:
        d = super().to_internal_value(data)
        return bk_app.TCPSocketAction(**d)


class HTTPHeaderInputSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="标头名称")
    value = serializers.CharField(help_text="标头值")

    def to_internal_value(self, data) -> bk_app.HTTPHeader:
        d = super().to_internal_value(data)
        return bk_app.HTTPHeader(**d)


class HTTPGetActionInputSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="探活端口")
    path = serializers.CharField(help_text="探活路径", max_length=128)
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)
    httpHeaders = serializers.ListField(help_text="HTTP 请求标头", required=False, child=HTTPHeaderInputSLZ())
    scheme = serializers.CharField(help_text="http/https", required=False)

    def to_internal_value(self, data) -> bk_app.HTTPGetAction:
        d = super().to_internal_value(data)
        return bk_app.HTTPGetAction(**d)


class ProbeInputSLZ(serializers.Serializer):
    """探针配置"""

    exec = ExecActionInputSLZ(help_text="exec 探活配置", required=False, allow_null=True)
    httpGet = HTTPGetActionInputSLZ(help_text="http get 探活配置", required=False, allow_null=True)
    tcpSocket = TCPSocketActionInputSLZ(help_text="tcp socket 探活配置", required=False, allow_null=True)
    initialDelaySeconds = serializers.IntegerField(help_text="初次探测延迟时间")
    timeoutSeconds = serializers.IntegerField(help_text="探测超时时间")
    periodSeconds = serializers.IntegerField(help_text="探测周期")
    successThreshold = serializers.IntegerField(help_text="成功阈值")
    failureThreshold = serializers.IntegerField(help_text="失败阈值")

    def to_internal_value(self, data) -> bk_app.Probe:
        d = super().to_internal_value(data)
        return bk_app.Probe(**d)


class ProbeSetInputSLZ(serializers.Serializer):
    """探针集合"""

    liveness = ProbeInputSLZ(help_text="存活探针", required=False, allow_null=True)
    readiness = ProbeInputSLZ(help_text="就绪探针", required=False, allow_null=True)
    startup = ProbeInputSLZ(help_text="启动探针", required=False, allow_null=True)

    def to_internal_value(self, data) -> bk_app.ProbeSet:
        d = super().to_internal_value(data)
        return bk_app.ProbeSet(**d)


class ProcessInputSLZ(serializers.Serializer):
    """Validate the `processes` field."""

    name = serializers.RegexField(regex=PROC_TYPE_PATTERN, max_length=PROC_TYPE_MAX_LENGTH)
    replicas = serializers.IntegerField(min_value=0)
    resQuotaPlan = serializers.ChoiceField(choices=ResQuotaPlan.get_choices(), allow_null=True, default=None)
    targetPort = serializers.IntegerField(min_value=1, max_value=65535, allow_null=True, default=None)
    command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    autoscaling = AutoscalingSpecInputSLZ(allow_null=True, default=None)
    probes = ProbeSetInputSLZ(allow_null=True, default=None)

    def to_internal_value(self, data) -> bk_app.BkAppProcess:
        d = super().to_internal_value(data)
        return bk_app.BkAppProcess(**d)


class HooksInputSLZ(serializers.Serializer):
    """Validate the `hooks` field."""

    class HookInputSLZ(serializers.Serializer):
        command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
        args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)

    preRelease = HookInputSLZ(allow_null=True, default=None)

    def to_internal_value(self, data) -> bk_app.BkAppHooks:
        d = super().to_internal_value(data)
        return bk_app.BkAppHooks(**d)


class BkSaaSInputSLZ(serializers.Serializer):
    """Validate the `bkSaaS` field."""

    bkAppCode = serializers.CharField()
    moduleName = serializers.CharField(required=False, allow_null=True)


class ServiceDiscoveryInputSLZ(serializers.Serializer):
    """Validate the `serviceDiscovery` field."""

    bkSaaS = serializers.ListField(child=BkSaaSInputSLZ(), required=False, allow_empty=True)

    def to_internal_value(self, data) -> bk_app.SvcDiscConfig:
        d = super().to_internal_value(data)
        return bk_app.SvcDiscConfig(**d)


class HostAliasSLZ(serializers.Serializer):
    ip = serializers.IPAddressField()
    hostnames = serializers.ListField(child=serializers.CharField())


class DomainResolutionInputSLZ(serializers.Serializer):
    nameservers = serializers.ListField(child=serializers.IPAddressField(), required=False)
    hostAliases = serializers.ListField(child=HostAliasSLZ(), required=False)

    def to_internal_value(self, data) -> bk_app.DomainResolution:
        d = super().to_internal_value(data)
        return bk_app.DomainResolution(**d)


class BkAppSpecInputSLZ(serializers.Serializer):
    """Validate the `spec` field of BkApp resource."""

    build = BuildInputSLZ(allow_null=True, default=None)
    processes = serializers.ListField(child=ProcessInputSLZ())
    configuration = ConfigurationInputSLZ(required=False)
    addons = serializers.ListField(child=AddonInputSLZ(), required=False, allow_empty=True)
    mounts = serializers.ListField(child=MountInputSLZ(), required=False, allow_empty=True)
    hooks = HooksInputSLZ(allow_null=True, default=None)
    envOverlay = EnvOverlayInputSLZ(required=False)
    svcDiscovery = ServiceDiscoveryInputSLZ(required=False)
    domainResolution = DomainResolutionInputSLZ(required=False)
