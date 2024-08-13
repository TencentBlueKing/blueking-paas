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

from typing import Dict

import yaml
from rest_framework.exceptions import ValidationError

from paasng.platform.bkapp_model.entities import v1alpha2 as v1alpha2_entity
from paasng.platform.bkapp_model.entities_syncer import (
    sync_addons,
    sync_build,
    sync_domain_resolution,
    sync_env_vars,
    sync_hooks,
    sync_mounts,
    sync_proc_env_overlays,
    sync_processes,
    sync_svc_discovery,
)
from paasng.platform.bkapp_model.serializers import v1alpha2 as v1alpha2_slz
from paasng.platform.modules.models import Module

from .exceptions import ManifestImportError


def import_manifest_yaml(module: Module, input_yaml_data: str):
    """Import a BkApp manifest to the current module in YAML format, see `import_manifest()`."""
    manifest = yaml.safe_load(input_yaml_data)
    return import_manifest(module, manifest)


def import_manifest(module: Module, input_data: Dict, reset_overlays_when_absent: bool = True):
    """Import a BkApp manifest to the current module, will overwrite existing data.

    :param module: The module object.
    :param input_data: The input manifest, only BkApp resource is supported.
    :param reset_overlays_when_absent: Whether to reset overlay data if the field is
        not found in the input manifest, default is True.
    :raises ManifestImportError: When unexpected error happened.
    """
    spec_slz = v1alpha2_slz.BkAppSpecInputSLZ(data=input_data["spec"])
    try:
        spec_slz.is_valid(raise_exception=True)
    except ValidationError as e:
        raise ManifestImportError.from_validation_error(e)

    spec_entity: v1alpha2_entity.BkAppSpec = spec_slz.validated_data
    import_bkapp_spec_entity(module, spec_entity, reset_overlays_when_absent)


def import_bkapp_spec_entity(
    module: Module, spec_entity: v1alpha2_entity.BkAppSpec, reset_overlays_when_absent: bool = True
):
    """Import a BkApp spec entity to the current module, will overwrite existing data.

    :param module: The module object.
    :param spec_entity: BkApp spec entity.
    :param reset_overlays_when_absent: Whether to reset overlay data if the field is
        not found in the input manifest, default is True.
    """
    env_vars, overlay_env_vars = [], []
    mounts = spec_entity.mounts or []
    if configuration := spec_entity.configuration:
        env_vars = configuration.env or []

    overlay_replicas, overlay_res_quotas, overlay_autoscaling, overlay_mounts = [], [], [], []
    if env_overlay := spec_entity.env_overlay:
        overlay_replicas = env_overlay.replicas or []
        overlay_res_quotas = env_overlay.res_quotas or []
        overlay_env_vars = env_overlay.env_variables or []
        overlay_autoscaling = env_overlay.autoscaling or []
        overlay_mounts = env_overlay.mounts or []

    # Run sync functions
    sync_processes(module, processes=spec_entity.processes)
    if build := spec_entity.build:
        sync_build(module, build)
    if hooks := spec_entity.hooks:
        sync_hooks(module, hooks)
    if env_vars or overlay_env_vars:
        sync_env_vars(module, env_vars, overlay_env_vars)
    if addons := spec_entity.addons:
        sync_addons(module, addons)
    if mounts or overlay_mounts:
        sync_mounts(module, mounts, overlay_mounts)
    if svc_discovery := spec_entity.svc_discovery:
        sync_svc_discovery(module, svc_discovery)
    if domain_resolution := spec_entity.domain_resolution:
        sync_domain_resolution(module, domain_resolution)

    # Finish the import if no overlay data is found and reset flag is False
    if not reset_overlays_when_absent and not any((overlay_replicas, overlay_res_quotas, overlay_autoscaling)):
        return

    # NOTE: Must import the processes first to create the ModuleProcessSpec objs
    sync_proc_env_overlays(module, overlay_replicas, overlay_res_quotas, overlay_autoscaling)
