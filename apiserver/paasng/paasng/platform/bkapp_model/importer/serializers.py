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
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.constants import ScalingPolicy
from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.platform.engine.constants import AppEnvName, ImagePullPolicy
from paasng.utils.serializers import field_env_var_key
from paasng.utils.validators import PROC_TYPE_PATTERN


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


class BaseMountFields(serializers.Serializer):
    """Base fields for validating Mount."""

    class SourceInputSLZ(serializers.Serializer):
        class ConfigMapInputSLZ(serializers.Serializer):
            name = serializers.CharField()

        configMap = ConfigMapInputSLZ()

    name = serializers.RegexField(regex=r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', max_length=63)
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
    plan = serializers.CharField()

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


class ProcessInputSLZ(serializers.Serializer):
    """Validate the `processes` field."""

    name = serializers.RegexField(regex=PROC_TYPE_PATTERN)
    replicas = serializers.IntegerField(min_value=0)
    resQuotaPlan = serializers.CharField(allow_null=True, default=None)
    targetPort = serializers.IntegerField(min_value=1, max_value=65535, allow_null=True, default=None)
    command = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    args = serializers.ListField(child=serializers.CharField(), allow_null=True, default=None)
    autoscaling = AutoscalingSpecInputSLZ(allow_null=True, default=None)

    # v1alpha1
    image = serializers.CharField(allow_null=True, default=None, allow_blank=True)
    imagePullPolicy = serializers.ChoiceField(choices=ImagePullPolicy.get_choices(), allow_null=True, default=None)
    cpu = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    memory = serializers.CharField(required=False, allow_blank=True, allow_null=True)

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


class BkAppSpecInputSLZ(serializers.Serializer):
    """Validate the `spec` field of BkApp resource."""

    build = BuildInputSLZ(allow_null=True, default=None)
    processes = serializers.ListField(child=ProcessInputSLZ())
    configuration = ConfigurationInputSLZ(required=False)
    mounts = serializers.ListField(child=MountInputSLZ(), required=False, allow_empty=True)
    hooks = HooksInputSLZ(allow_null=True, default=None)
    envOverlay = EnvOverlayInputSLZ(required=False)
