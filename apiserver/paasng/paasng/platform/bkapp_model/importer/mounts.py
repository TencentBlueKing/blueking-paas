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
from typing import List

from paas_wl.bk_app.cnative.specs.constants import MountEnvName
from paas_wl.bk_app.cnative.specs.crd.bk_app import Mount as MountSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import MountOverlay
from paas_wl.bk_app.cnative.specs.models import Mount
from paasng.platform.modules.models import Module

from .entities import CommonImportResult


def import_mounts(module: Module, mounts: List[MountSpec], overlay_mounts: List[MountOverlay]) -> CommonImportResult:
    """Import mount relations, existing data that is not in the input list may be removed.

    :param mounts: The mount relations that available for all environments.
    :param overlay_mounts: The environment-specified mount relations.
    :return: A result object.
    """
    existing_mounts = Mount.objects.filter(module_id=module.id)
    existing_index = {(m.mount_path, m.environment_name): m.id for m in existing_mounts}

    ret = CommonImportResult()
    for mount in mounts:
        _, created = Mount.objects.update_or_create(
            module_id=module.id,
            mount_path=mount.mountPath,
            environment_name=MountEnvName.GLOBAL.value,
            defaults={"source_config": mount.source},
        )
        ret.incr_by_created_flag(created)
        # Remove it from index if it already exists
        existing_index.pop((mount.mountPath, MountEnvName.GLOBAL.value), None)

    for overlay_mount in overlay_mounts:
        _, created = Mount.objects.update_or_create(
            module_id=module.id,
            mount_path=overlay_mount.mountPath,
            environment_name=overlay_mount.envName,
            defaults={"source_config": overlay_mount.source},
        )
        ret.incr_by_created_flag(created)
        # Remove it from index if it already exists
        existing_index.pop((overlay_mount.mountPath, overlay_mount.envName), None)

    # Remove existing relations that is not touched.
    ret.deleted_num, _ = Mount.objects.filter(id__in=existing_index.values()).delete()
    return ret
