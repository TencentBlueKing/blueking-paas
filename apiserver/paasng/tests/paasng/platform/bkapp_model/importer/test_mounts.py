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
import functools

import pytest

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource, MountOverlay, VolumeSource
from paas_wl.bk_app.cnative.specs.crd.bk_app import Mount as MountSpec
from paas_wl.bk_app.cnative.specs.models import Mount
from paasng.platform.bkapp_model.importer.mounts import import_mounts

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class Test__import_mounts:
    def test_integrated(self, bk_module):
        create_mount = functools.partial(
            Mount.objects.create,
            module_id=bk_module.id,
            name="nginx",
            source_type=VolumeSourceType.ConfigMap,
            source_config=VolumeSource(configMap=ConfigMapSource(name="nginx-configmap")),
        )
        create_mount(mount_path="/etc/conf", environment_name=MountEnvName.GLOBAL.value)
        create_mount(mount_path="/etc/conf_stag", environment_name=MountEnvName.STAG.value)
        create_mount(mount_path="/etc/conf_stag_2", environment_name=MountEnvName.STAG.value)
        create_mount(mount_path="/etc/conf_prod", environment_name=MountEnvName.PROD.value)
        assert Mount.objects.count() == 4

        ret = import_mounts(
            bk_module,
            [
                MountSpec(
                    mountPath="/etc/conf_another",
                    name="nginx_another",
                    source=VolumeSource(configMap=ConfigMapSource(name="nginx-configmap")),
                )
            ],
            [
                MountOverlay(
                    envName="stag",
                    mountPath="/etc/conf_stag",
                    name="nginx_stag",
                    source=VolumeSource(configMap=ConfigMapSource(name="nginx-foobar")),
                )
            ],
        )
        assert Mount.objects.count() == 2
        assert ret.created_num == 1
        assert ret.updated_num == 1
        assert ret.deleted_num == 3
