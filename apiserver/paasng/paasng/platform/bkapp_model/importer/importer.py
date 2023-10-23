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
from typing import Dict

import yaml
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay
from paasng.platform.bkapp_model.importer.env_vars import import_env_vars
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module
from paasng.utils.serializers import field_env_var_key

from .exceptions import ManifestImportError


class ConfigurationInputSLZ(serializers.Serializer):
    """Validate the `configuration` field."""

    class EnvVarInputSLZ(serializers.Serializer):
        name = field_env_var_key()
        value = serializers.CharField(allow_blank=False)

        def to_internal_value(self, data) -> EnvVar:
            # NOTE: Should we define another "EnvVar" type instead of importing from the crd module?
            d = super().to_internal_value(data)
            return EnvVar(**d)

    env = serializers.ListField(child=EnvVarInputSLZ())


class EnvOverlayInputSLZ(serializers.Serializer):
    """Validate the `envOverlay` field."""

    class EnvVarOverlayInputSLZ(serializers.Serializer):
        envName = serializers.ChoiceField(choices=AppEnvName.get_choices())
        name = field_env_var_key()
        value = serializers.CharField(allow_blank=False)

        def to_internal_value(self, data) -> EnvVarOverlay:
            d = super().to_internal_value(data)
            return EnvVarOverlay(**d)

    envVariables = serializers.ListField(child=EnvVarOverlayInputSLZ())


class BkAppSpecInputSLZ(serializers.Serializer):
    """Validate the `spec` field of BkApp resource."""

    configuration = ConfigurationInputSLZ(required=False)
    envOverlay = EnvOverlayInputSLZ(required=False)


def import_manifest_yaml(module: Module, input_yaml_data: str):
    """Import a BkApp manifest to the current module in YAML format, see `import_manifest()`."""
    manifest = yaml.safe_load(input_yaml_data)
    return import_manifest(module, manifest)


def import_manifest(module: Module, input_data: Dict):
    """Import a BkApp manifest to the current module, will overwrite existing data.

    :param module: The module object.
    :param input_data: The input manifest, only BkApp resource is supported.
    :raises ManifestImportError: When unexpected error happened.
    """
    # TODO: Standardize input_data which is using apiVersion other than "v1alpha2".
    spec_slz = BkAppSpecInputSLZ(data=input_data['spec'])
    try:
        spec_slz.is_valid(raise_exception=True)
    except ValidationError as e:
        raise ManifestImportError.from_validation_error(e)

    if configuration := spec_slz.validated_data['configuration']:
        env_vars = configuration.get('env', [])
    if env_overlay := spec_slz.validated_data['envOverlay']:
        overlay_env_vars = env_overlay.get('envVariables', [])

    import_env_vars(module, env_vars, overlay_env_vars)
