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
from rest_framework.exceptions import ValidationError

from paasng.platform.bkapp_model.importer.addons import import_addons
from paasng.platform.bkapp_model.importer.build import import_build
from paasng.platform.bkapp_model.importer.domain_resolution import import_domain_resolution
from paasng.platform.bkapp_model.importer.env_overlays import import_env_overlays
from paasng.platform.bkapp_model.importer.env_vars import import_env_vars
from paasng.platform.bkapp_model.importer.hooks import import_hooks
from paasng.platform.bkapp_model.importer.mounts import import_mounts
from paasng.platform.bkapp_model.importer.processes import import_processes
from paasng.platform.bkapp_model.importer.serializers import BkAppSpecInputSLZ
from paasng.platform.bkapp_model.importer.svc_discovery import import_svc_discovery
from paasng.platform.modules.models import Module

from .exceptions import ManifestImportError


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
    spec_slz = BkAppSpecInputSLZ(data=input_data["spec"])
    try:
        spec_slz.is_valid(raise_exception=True)
    except ValidationError as e:
        raise ManifestImportError.from_validation_error(e)

    validated_data = spec_slz.validated_data

    env_vars, overlay_env_vars = [], []
    mounts = validated_data.get("mounts", [])
    if configuration := validated_data.get("configuration", {}):
        env_vars = configuration.get("env", [])

    overlay_replicas, overlay_res_quotas, overlay_autoscaling, overlay_mounts = [], [], [], []
    if env_overlay := validated_data.get("envOverlay", {}):
        overlay_replicas = env_overlay.get("replicas", [])
        overlay_res_quotas = env_overlay.get("resQuotas", [])
        overlay_env_vars = env_overlay.get("envVariables", [])
        overlay_autoscaling = env_overlay.get("autoscaling", [])
        overlay_mounts = env_overlay.get("mounts", [])

    # Run importer functions
    import_processes(module, processes=validated_data["processes"])
    if build := validated_data.get("build"):
        import_build(module, build)
    if hooks := validated_data.get("hooks"):
        import_hooks(module, hooks)
    if env_vars or overlay_env_vars:
        import_env_vars(module, env_vars, overlay_env_vars)
    if addons := validated_data.get("addons"):
        import_addons(module, addons)
    if mounts or overlay_mounts:
        import_mounts(module, mounts, overlay_mounts)
    if svc_discovery := validated_data.get("svcDiscovery"):
        import_svc_discovery(module, svc_discovery)
    if domain_resolution := validated_data.get("domainResolution"):
        import_domain_resolution(module, domain_resolution)

    # NOTE: Must import the processes first to create the ModuleProcessSpec objs
    import_env_overlays(module, overlay_replicas, overlay_res_quotas, overlay_autoscaling)
