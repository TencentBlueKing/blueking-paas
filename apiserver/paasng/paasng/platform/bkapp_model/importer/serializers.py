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

from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay, Mount, MountOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.serializers import field_env_var_key


class BaseEnvVarFields(serializers.Serializer):
    """Base fields for validating EnvVar."""

    name = field_env_var_key()
    value = serializers.CharField(allow_blank=False)


class EnvVarInputSLZ(BaseEnvVarFields):
    def to_internal_value(self, data) -> EnvVar:
        # NOTE: Should we define another "EnvVar" type instead of importing from the crd module?
        d = super().to_internal_value(data)
        return EnvVar(**d)


class EnvVarOverlayInputSLZ(BaseEnvVarFields):
    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())

    def to_internal_value(self, data) -> EnvVarOverlay:
        d = super().to_internal_value(data)
        return EnvVarOverlay(**d)


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

    def to_internal_value(self, data) -> Mount:
        d = super().to_internal_value(data)
        return Mount(**d)


class MountOverlayInputSLZ(BaseMountFields):
    """Validate the `mounts` field in envOverlay."""

    envName = serializers.ChoiceField(choices=AppEnvName.get_choices())

    def to_internal_value(self, data) -> MountOverlay:
        d = super().to_internal_value(data)
        return MountOverlay(**d)


class ConfigurationInputSLZ(serializers.Serializer):
    """Validate the `configuration` field."""

    env = serializers.ListField(child=EnvVarInputSLZ())


class EnvOverlayInputSLZ(serializers.Serializer):
    """Validate the `envOverlay` field."""

    envVariables = serializers.ListField(child=EnvVarOverlayInputSLZ(), required=False)
    mounts = serializers.ListField(child=MountOverlayInputSLZ(), required=False)


class BkAppSpecInputSLZ(serializers.Serializer):
    """Validate the `spec` field of BkApp resource."""

    configuration = ConfigurationInputSLZ(required=False)
    mounts = serializers.ListField(child=MountInputSLZ(), required=False, allow_empty=True)
    envOverlay = EnvOverlayInputSLZ(required=False)
