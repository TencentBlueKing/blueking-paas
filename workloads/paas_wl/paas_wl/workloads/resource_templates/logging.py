# -*- coding: utf-8 -*-
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

import cattr
from django.conf import settings

from paas_wl.platform.applications.models.app import App
from paas_wl.platform.applications.models.managers.app_metadata import get_metadata
from paas_wl.workloads.resource_templates.components.volume import Volume, VolumeMount


def get_app_logging_volume(app) -> List[Volume]:
    """获取应用(挂载到宿主机的)日志卷配置, 如果应用不支持挂载日志到宿主机, 返回空列表"""
    if not app.latest_config.mount_log_to_host:
        return []

    mdata = get_metadata(app)
    # NOTE: DO NOT CHANGE `legacy_log_path` and `log_path_prefix` unless the log collection policy is adjusted
    legacy_log_path = f"{app.region}-{app.scheduler_safe_name}"
    # assemble some shortcuts
    # /data/bkapp/v3logs/ieod-xxx_xxx-stag/default/
    module_log_path = f"{app.region}-bkapp-{mdata.get_paas_app_code()}-{mdata.environment}/{mdata.module_name}"
    return cattr.structure(
        [
            {
                'name': settings.VOLUME_NAME_APP_LOGGING,
                'hostPath': {"path": f"{settings.VOLUME_HOST_PATH_APP_LOGGING_DIR}/{legacy_log_path}"},
            },
            {
                'name': settings.MUL_MODULE_VOLUME_NAME_APP_LOGGING,
                'hostPath': {"path": f"{settings.MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR}/{module_log_path}"},
            },
        ],
        List[Volume],
    )


def get_app_logging_volume_mounts(app: App) -> List[VolumeMount]:
    """获取应用(挂载到宿主机的)日志卷挂载到容器的挂载点配置, 如果应用不支持挂载日志到宿主机, 返回空列表"""
    if not app.latest_config.mount_log_to_host:
        return []

    return cattr.structure(
        [
            {
                'name': settings.VOLUME_NAME_APP_LOGGING,
                'mountPath': settings.VOLUME_MOUNT_APP_LOGGING_DIR,
            },
            {
                'name': settings.MUL_MODULE_VOLUME_NAME_APP_LOGGING,
                'mountPath': settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
            },
        ],
        List[VolumeMount],
    )
