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

from paasng.platform.agent_sandbox.e2b.constants import (
    GATEWAY_TEMPLATE_LABEL,
    TEMPLATE_MANAGED_BY_LABEL,
    TEMPLATE_MANAGED_BY_VALUE,
)
from paasng.platform.agent_sandbox.e2b.template_sync import manifests
from tests.paasng.platform.agent_sandbox.e2b.helpers import IMAGE, make_builtin_template, make_custom_template

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

NAMESPACE = "e2b-system"
MANAGED_LABELS = {TEMPLATE_MANAGED_BY_LABEL: TEMPLATE_MANAGED_BY_VALUE}


class TestManifests:
    def test_template_manifest(self, settings):
        settings.AGENT_SANDBOX_E2B_TEMPLATE_STORAGE_CLASS = "cbs-ssd"
        template = make_builtin_template(
            "e2b-envd", cpu_count=4, memory_mb=8192, disk_size_mb=1000, env_vars={"B": "2", "A": "1"}, workdir="/w"
        )

        manifest = manifests.build_template_manifest(template, NAMESPACE)

        assert manifest["kind"] == "SandboxTemplate"
        assert manifest["metadata"] == {"name": "e2b-envd", "namespace": NAMESPACE, "labels": MANAGED_LABELS}
        spec = manifest["spec"]["template"]
        assert spec["metadata"]["labels"] == {GATEWAY_TEMPLATE_LABEL: "e2b-envd"}
        domain = spec["spec"]["domain"]
        assert domain["cpu"] == {"cores": 4}
        assert domain["memory"] == "8192Mi"
        assert domain["devices"]["disks"][0]["size"] == "1000Mi"
        (container,) = spec["spec"]["podTemplate"]["containers"]
        assert container["image"] == IMAGE
        assert container["env"] == [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]
        assert container["workingDir"] == "/w"
        (pvc,) = spec["spec"]["volumeClaimTemplates"]
        # 盘镜像文件放在 PVC 上，要给文件系统开销留余量
        assert pvc["spec"]["resources"]["requests"]["storage"] == "1500Mi"
        assert pvc["spec"]["storageClassName"] == "cbs-ssd"

    def test_omits_empty_optional_fields(self):
        """不填系统盘时，与集群里已有的 e2b-python 等模板一样，不声明盘与 PVC"""
        template = make_builtin_template("e2b-envd", disk_size_mb=None)

        spec = manifests.build_template_manifest(template, NAMESPACE)["spec"]["template"]["spec"]

        assert spec["domain"] == {"cpu": {"cores": 2}, "memory": "4096Mi"}
        assert spec["podTemplate"] == {
            "containers": [{"name": "main", "image": IMAGE, "imagePullPolicy": "IfNotPresent"}]
        }
        assert "volumeClaimTemplates" not in spec

    def test_builtin_pool_is_prewarmed(self):
        template = make_builtin_template("e2b-envd", prewarm_count=3)

        manifest = manifests.build_pool_manifest(template, NAMESPACE)

        assert manifest["metadata"]["labels"] == MANAGED_LABELS
        assert manifest["spec"] == {"replicas": 3, "templateRef": {"name": "e2b-envd"}}

    def test_custom_pool_is_cold(self, bk_app):
        """自定义模板不预热，网关在无库存时现场创建"""
        template = make_custom_template(bk_app, "mine", prewarm_count=5)

        manifest = manifests.build_pool_manifest(template, NAMESPACE)

        assert manifest["spec"] == {"replicas": 0, "templateRef": {"name": template.resource_name}}
