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
from paas_wl.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.cnative.specs.crd import bk_app
from paas_wl.cnative.specs.models import BkAppResource, Mount
from paas_wl.configuration.configmap.entities import ConfigMap, configmap_kmodel
from paasng.platform.applications.models import ModuleEnvironment


class MountsManager:
    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def inject_to_bkapp(self, manifest: BkAppResource):
        """将 mounts 配置注入到 BkApp 模型中"""
        if mount_queryset := Mount.objects.filter(
            module=self.env.module, environment_name__in=[self.env.environment, MountEnvName.GLOBAL.value]
        ):
            # TODO 处理用户可能在 bkapp.yaml 中定义 mounts 的场景
            manifest.spec.mounts = [
                bk_app.Mount(
                    name=m.name,
                    mountPath=m.mount_path,
                    source=m.source_config,
                )
                for m in mount_queryset
            ]


class VolumeSourceManager:
    """"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.wl_app = env.wl_app

    def deploy(self):
        """部署卷"""
        mount_queryset = Mount.objects.filter(
            module=self.env.module, environment_name__in=[self.env.environment, MountEnvName.GLOBAL.value]
        )
        for m in mount_queryset:
            self._upsert(m)

    def _upsert(self, mount: Mount):
        if mount.source_type == VolumeSourceType.ConfigMap:
            configmap_kmodel.upsert(ConfigMap(app=self.wl_app, name=mount.source.name, data=mount.source.data))
