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

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import v1alpha2 as v1alpha2_entity
from paasng.platform.bkapp_model.entities_syncer import (
    clean_empty_overlays,
    sync_addons,
    sync_build,
    sync_domain_resolution,
    sync_env_overlays_autoscalings,
    sync_env_overlays_replicas,
    sync_env_overlays_res_quotas,
    sync_env_vars,
    sync_hooks,
    sync_mounts,
    sync_observability,
    sync_processes,
    sync_svc_discovery,
)
from paasng.platform.bkapp_model.serializers import v1alpha2 as v1alpha2_slz
from paasng.platform.modules.models import Module
from paasng.utils.structure import NOTSET, NotSetType

from .exceptions import ManifestImportError


def import_manifest_yaml(module: Module, input_yaml_data: str, manager: fieldmgr.ManagerType):
    """Import a BkApp manifest to the current module in YAML format, see `import_manifest()`."""
    manifest = yaml.safe_load(input_yaml_data)
    return import_manifest(module, manifest, manager)


def import_manifest(module: Module, input_data: Dict, manager: fieldmgr.ManagerType):
    """Import a BkApp manifest to the current module, will overwrite existing data.

    :param module: The module object.
    :param input_data: The input manifest, only BkApp resource is supported.
    :param manager: The manager performing this action.
    :raises ManifestImportError: When unexpected error happened.
    """
    spec_slz = v1alpha2_slz.BkAppSpecInputSLZ(data=input_data["spec"])
    try:
        spec_slz.is_valid(raise_exception=True)
    except ValidationError as e:
        raise ManifestImportError.from_validation_error(e)

    spec_entity: v1alpha2_entity.BkAppSpec = spec_slz.validated_data
    import_bkapp_spec_entity(module, spec_entity, manager)


def import_bkapp_spec_entity(module: Module, spec_entity: v1alpha2_entity.BkAppSpec, manager: fieldmgr.ManagerType):
    """Import a BkApp spec entity to the current module, will overwrite existing data.

    :param module: The module object.
    :param spec_entity: BkApp spec entity.
    :param manager: The manager performing this action.
    """
    env_vars = []
    mounts = spec_entity.mounts or []
    if configuration := spec_entity.configuration:
        env_vars = configuration.env or []

    # Initialize a bunch of overlay data
    overlay_replicas: NotSetType | list = NOTSET
    overlay_res_quotas: NotSetType | list = NOTSET
    overlay_env_vars: NotSetType | list = NOTSET
    overlay_autoscaling: NotSetType | list = NOTSET
    overlay_mounts: NotSetType | list = NOTSET
    if not isinstance(spec_entity.env_overlay, NotSetType):
        eo = spec_entity.env_overlay
        if eo:
            overlay_replicas = eo.replicas or []
            overlay_res_quotas = eo.res_quotas or []
            overlay_env_vars = eo.env_variables or []
            overlay_autoscaling = eo.autoscaling or []
            overlay_mounts = eo.mounts or []

    # Run sync functions
    sync_processes(module, processes=spec_entity.processes)
    if build := spec_entity.build:
        sync_build(module, build)
    if hooks := spec_entity.hooks:
        sync_hooks(module, hooks)
    if env_vars or overlay_env_vars:
        # sync_env_vars doesn't need to use manager parameter because the data will
        # only be manged by a single manger.
        # TODO: Use preset env vars instead / always call even if the value is None or NOTSET
        sync_env_vars(module, env_vars, overlay_env_vars)
    if addons := spec_entity.addons:
        sync_addons(module, addons)
    if mounts or overlay_mounts:
        sync_mounts(module, mounts, overlay_mounts, manager)

    sync_svc_discovery(module, spec_entity.svc_discovery, manager)
    sync_domain_resolution(module, spec_entity.domain_resolution, manager)

    sync_observability(module, spec_entity.observability)

    # NOTE: Must import the processes first to create the ModuleProcessSpec objs
    sync_env_overlays_replicas(module, overlay_replicas, manager)
    sync_env_overlays_res_quotas(module, overlay_res_quotas, manager)
    sync_env_overlays_autoscalings(module, overlay_autoscaling, manager)

    clean_empty_overlays(module)
