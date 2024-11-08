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

from paas_wl.bk_app.cnative.specs.constants import MountEnvName
from paas_wl.bk_app.cnative.specs.crd import bk_app
from paas_wl.bk_app.cnative.specs.models import Mount as MountDB
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import Mount, MountOverlay
from paasng.platform.modules.models import Module
from paasng.utils.camel_converter import dict_to_camel
from paasng.utils.structure import NotSetType

from .result import CommonSyncResult


def sync_mounts(
    module: Module, mounts: List[Mount], overlay_mounts: List[MountOverlay] | NotSetType, manager: fieldmgr.ManagerType
) -> CommonSyncResult:
    """Sync mount relations to db model, existing data that is not in the input list may be removed.

    :param mounts: The mount relations that available for all environments.
    :param overlay_mounts: The environment-specified mount relations.
    :param manager: The manager performing this action.
    :return: sync result.
    """
    # TODO: handle fields manager related logic
    existing_mounts = MountDB.objects.filter(module_id=module.id)
    existing_index = {(m.mount_path, m.environment_name): m.id for m in existing_mounts}

    ret = CommonSyncResult()
    for mount in mounts:
        source_config = bk_app.VolumeSource(**dict_to_camel(mount.source.dict()))
        _, created = MountDB.objects.update_or_create(
            module_id=module.id,
            mount_path=mount.mount_path,
            environment_name=MountEnvName.GLOBAL.value,
            defaults={"source_config": source_config},
        )
        ret.incr_by_created_flag(created)
        # Remove it from index if it already exists
        existing_index.pop((mount.mount_path, MountEnvName.GLOBAL.value), None)

    if isinstance(overlay_mounts, NotSetType):
        overlay_mounts = []
    for overlay_mount in overlay_mounts:
        source_config = bk_app.VolumeSource(**dict_to_camel(overlay_mount.source.dict()))
        _, created = MountDB.objects.update_or_create(
            module_id=module.id,
            mount_path=overlay_mount.mount_path,
            environment_name=overlay_mount.env_name,
            defaults={"source_config": source_config},
        )
        ret.incr_by_created_flag(created)
        # Remove it from index if it already exists
        existing_index.pop((overlay_mount.mount_path, overlay_mount.env_name), None)

    # Remove existing relations that is not touched.
    ret.deleted_num, _ = MountDB.objects.filter(id__in=existing_index.values()).delete()
    return ret
