# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import pytest

from paas_wl.bk_app.processes.entities import SecretFileMount
from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.bk_app.processes.kres_slzs import secret_file_volume_mounts, secret_file_volumes
from paas_wl.infras.resource_templates.managers import AddonManager
from paas_wl.infras.resources.kube_res.base import AppEntityManager

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

MOUNT = SecretFileMount(
    volume_name="kms-secret",
    secret_name="kms-res-1",
    mount_dir="/etc/kms",
    sub_paths=("envelope", "privateKey"),
)

MOUNT_ENVELOPE = {"name": "kms-secret", "mountPath": "/etc/kms/envelope", "subPath": "envelope", "readOnly": True}
MOUNT_PRIVATE_KEY = {
    "name": "kms-secret",
    "mountPath": "/etc/kms/privateKey",
    "subPath": "privateKey",
    "readOnly": True,
}
VOLUME = {"name": "kms-secret", "secret": {"secretName": "kms-res-1"}}


class TestSecretFileHelpers:
    def test_volumes_and_mounts(self):
        assert secret_file_volumes([MOUNT]) == [VOLUME]
        assert secret_file_volume_mounts([MOUNT]) == [MOUNT_ENVELOPE, MOUNT_PRIVATE_KEY]

    def test_empty(self):
        assert secret_file_volumes([]) == []
        assert secret_file_volume_mounts([]) == []


class TestPodSpecSecretMounts:
    @pytest.fixture()
    def serializer(self, wl_app):
        return AppEntityManager(Process)._make_serializer(wl_app)  # type: ignore

    @pytest.fixture()
    def process(self, wl_release):
        return Process.from_release(type_="web", release=wl_release)

    def test_main_container_gets_secret_files(self, serializer, process):
        process.runtime.secret_mounts = [MOUNT]

        spec = serializer._construct_pod_body_specs(process)  # type: ignore

        main_container = spec["containers"][0]
        assert MOUNT_ENVELOPE in main_container["volumeMounts"]
        assert MOUNT_PRIVATE_KEY in main_container["volumeMounts"]
        assert VOLUME in spec["volumes"]

    def test_sidecars_do_not_get_secret_files(self, serializer, process, mocker):
        mocker.patch.object(AddonManager, "get_sidecars", return_value=[{"name": "sidecar", "image": "sidecar:1"}])
        process.runtime.secret_mounts = [MOUNT]

        spec = serializer._construct_pod_body_specs(process)  # type: ignore

        sidecar = spec["containers"][1]
        assert sidecar["name"] == "sidecar"
        assert all(mount["name"] != "kms-secret" for mount in sidecar.get("volumeMounts", []))

    def test_no_secret_files_by_default(self, serializer, process):
        spec = serializer._construct_pod_body_specs(process)  # type: ignore

        assert all(mount["name"] != "kms-secret" for mount in spec["containers"][0]["volumeMounts"])
        assert all(volume["name"] != "kms-secret" for volume in spec["volumes"])
