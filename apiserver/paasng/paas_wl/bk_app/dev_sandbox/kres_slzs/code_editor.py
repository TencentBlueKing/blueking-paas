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

from typing import TYPE_CHECKING, Dict, Optional

import cattr
from django.conf import settings
from kubernetes.dynamic import ResourceField, ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.conf import CODE_SVC_PORT_PAIRS
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Resources, Runtime, Status
from paas_wl.bk_app.dev_sandbox.kres_slzs.sandbox import get_dev_sandbox_labels
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.utils.dictx import get_items

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import CodeEditor

_CONTAINER_NAME = "code-editor"


class CodeEditorSerializer(AppEntitySerializer["CodeEditor"]):
    def serialize(self, obj: "CodeEditor", original_obj: Optional[ResourceInstance] = None, **kwargs):
        labels = get_dev_sandbox_labels(obj.app)
        deployment_body = {
            "apiVersion": self.get_apiversion(),
            "kind": "Deployment",
            "metadata": {
                "name": obj.name,
                "labels": labels,
            },
            "spec": {
                "replicas": 1,
                "revisionHistoryLimit": settings.MAX_RS_RETAIN,
                "selector": {"matchLabels": labels},
                "template": {"metadata": {"labels": labels}, "spec": self._construct_pod_spec(obj)},
            },
        }
        return deployment_body

    def _construct_pod_spec(self, obj: "CodeEditor") -> Dict:
        main_container = {
            "name": _CONTAINER_NAME,
            "image": obj.runtime.image,
            "env": [{"name": str(key), "value": str(value)} for key, value in obj.runtime.envs.items()],
            "imagePullPolicy": obj.runtime.image_pull_policy,
            "ports": [{"containerPort": port_pair.target_port} for port_pair in CODE_SVC_PORT_PAIRS],
        }

        if obj.resources:
            main_container["resources"] = obj.resources.to_dict()

        spec = {"containers": [main_container]}
        self._construct_volume_mounts(obj, spec)

        return spec

    def _construct_volume_mounts(self, obj: "CodeEditor", spec: Dict):
        if not obj.config:
            return

        if start_dir := obj.config.start_dir:
            main_container = spec["containers"][0]
            main_container["volumeMounts"] = [{"name": "start-dir", "mountPath": start_dir}]

        if pvc_claim_name := obj.config.pvc_claim_name:
            spec["volumes"] = [
                {
                    "name": "start-dir",
                    "persistentVolumeClaim": {"claimName": pvc_claim_name},
                }
            ]


class CodeEditorDeserializer(AppEntityDeserializer["CodeEditor"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "CodeEditor":
        main_container = self._get_main_container(kube_data)
        runtime = cattr.structure(
            {
                "envs": {env.name: env.value for env in main_container.env if getattr(env, "value", None)},
                "image": main_container.image,
                "image_pull_policy": getattr(main_container, "imagePullPolicy", ImagePullPolicy.IF_NOT_PRESENT),
            },
            Runtime,
        )
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            runtime=runtime,
            resources=cattr.structure(getattr(main_container, "resources", None), Resources),
            config=self._construct_config(kube_data),
            status=Status(kube_data.status.get("replicas", 1), kube_data.status.get("readyReplicas", 0)),
        )

    def _get_main_container(self, deployment: ResourceInstance) -> ResourceField:
        pod_template = deployment.spec.template
        for c in pod_template.spec.containers:
            if c.name == _CONTAINER_NAME:
                return c

        raise RuntimeError(f"No {_CONTAINER_NAME} container found in resource")

    def _get_main_container_dict(self, deployment: ResourceInstance) -> Dict:
        deployment_dict = deployment.to_dict()
        containers = get_items(deployment_dict, "spec.template.spec.containers", [])
        for c in containers:
            if c["name"] == _CONTAINER_NAME:
                return c
        raise RuntimeError(f"No {_CONTAINER_NAME} container found in resource")

    def _construct_config(self, deployment: ResourceInstance) -> CodeEditorConfig:
        deployment_dict = deployment.to_dict()
        main_container_dict = self._get_main_container_dict(deployment)

        volume = get_items(deployment_dict, "spec.template.spec.volumes", [{}])[0]
        volume_mounts = get_items(main_container_dict, "volumeMounts", [{}])[0]
        env_list = get_items(main_container_dict, "env", [{}])
        envs = {env["name"]: env["value"] for env in env_list}
        config = cattr.structure(
            {
                "pvc_claim_name": get_items(volume, "persistentVolumeClaim.claimName"),
                "start_dir": get_items(volume_mounts, "mountPath"),
                "password": envs.get("PASSWORD"),
            },
            CodeEditorConfig,
        )

        return config
