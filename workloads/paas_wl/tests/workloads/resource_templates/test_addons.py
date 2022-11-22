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
import pytest

from paas_wl.workloads.resource_templates.components.probe import default_readiness_probe
from paas_wl.workloads.resource_templates.components.sidecar import Container
from paas_wl.workloads.resource_templates.utils import AddonManager

pytestmark = pytest.mark.django_db


class TestAppAddOns:
    def test_sidecar(self, app, sidecar_addon_template):
        sidecar_addon_template.link_to_app(app)
        sidecars = cattr.structure(AddonManager(app).get_sidecars(), List[Container])

        assert len(sidecars) == 1
        container = sidecars[0]

        assert container.name == "agent"
        assert container.ports
        assert container.ports[0].name == "some-config"
        assert container.ports[0].containerPort == 7788
        assert container.ports[0].protocol == "UDP"

    def test_default_readiness_probe(self, app):
        readiness_probe = AddonManager(app).get_readiness_probe()
        assert readiness_probe == default_readiness_probe

    def test_user_readiness_probe(self, app, probe_addon_template):
        probe_addon_template.link_to_app(app)
        readiness_probe = AddonManager(app).get_readiness_probe()
        assert readiness_probe != default_readiness_probe

        assert readiness_probe.httpGet
        assert readiness_probe.httpGet.port == 5000
        assert readiness_probe.httpGet.path == "/healthz"

    def test_shm_mount_point(self, app, shm_volume_mount_addon_template):
        assert len(AddonManager(app).get_volume_mounts()) == 0

        shm_volume_mount_addon_template.link_to_app(app)
        mounts = AddonManager(app).get_volume_mounts()
        assert len(mounts) == 1
        mount = mounts[0]

        assert mount.name == "shm"
        assert mount.mountPath == "/dev/shm"

    def test_shm_volume(self, app, shm_volume_addon_template):
        assert len(AddonManager(app).get_volumes()) == 0

        shm_volume_addon_template.link_to_app(app)
        volumes = AddonManager(app).get_volumes()
        assert len(volumes) == 1
        volume = volumes[0]

        assert volume.name == "shm"
        assert volume.emptyDir
        assert volume.emptyDir.medium == "Memory"
        assert volume.emptyDir.sizeLimit == "512Mi"

    def test_secret_volume(self, app, secret_volume_addon_template):
        assert len(AddonManager(app).get_volumes()) == 0

        secret_volume_addon_template.link_to_app(app)
        volumes = AddonManager(app).get_volumes()
        assert len(volumes) == 1
        volume = volumes[0]

        assert volume.name == "secret"
        assert volume.secret
        assert volume.secret.secretName == "the-secret"
        assert len(volume.secret.items) == 1
        assert volume.secret.items[0].key == "a"
        assert volume.secret.items[0].path == "secret/a"
        assert volume.secret.items[0].mode == 0o644
