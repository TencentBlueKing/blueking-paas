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
from django_dynamic_fixture import G

from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.infras.resource_templates.managers import AddonManager
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.workloads.release_controller.entities import SecretFileMount
from paas_wl.workloads.release_controller.hooks.kres_entities import Command, command_kmodel
from paas_wl.workloads.release_controller.hooks.models import Command as CommandModel

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


@pytest.fixture()
def process(wl_release):
    return Process.from_release(type_="web", release=wl_release)


def test_secret_files_only_mounted_to_main_container(wl_app, process, mocker):
    mocker.patch.object(AddonManager, "get_sidecars", return_value=[{"name": "sidecar", "image": "sidecar:1"}])
    process.runtime.secret_mounts = [MOUNT]

    spec = AppEntityManager(Process)._make_serializer(wl_app)._construct_pod_body_specs(process)  # type: ignore

    main_container, sidecar = spec["containers"]
    assert MOUNT_ENVELOPE in main_container["volumeMounts"]
    assert MOUNT_PRIVATE_KEY in main_container["volumeMounts"]
    assert VOLUME in spec["volumes"]
    assert all(mount["name"] != "kms-secret" for mount in sidecar.get("volumeMounts", []))


def test_secret_files_only_mounted_to_command_main_container(wl_app, wl_build, mocker):
    mocker.patch.object(AddonManager, "get_sidecars", return_value=[{"name": "sidecar", "image": "sidecar:1"}])
    command_model = G(CommandModel, app=wl_app, command="migrate", config=wl_app.latest_config, build=wl_build)
    command = Command.from_db_obj(command_model, secret_mounts=[MOUNT])

    pod = command_kmodel._make_serializer(wl_app).serialize(command)  # type: ignore

    main_container, sidecar = pod["spec"]["containers"]
    assert MOUNT_ENVELOPE in main_container["volumeMounts"]
    assert MOUNT_PRIVATE_KEY in main_container["volumeMounts"]
    assert VOLUME in pod["spec"]["volumes"]
    assert all(mount["name"] != "kms-secret" for mount in sidecar.get("volumeMounts", []))
