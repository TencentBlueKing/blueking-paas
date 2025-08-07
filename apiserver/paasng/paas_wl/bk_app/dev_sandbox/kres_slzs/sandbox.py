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

from typing import TYPE_CHECKING, Dict, List, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.conf import DEV_SANDBOX_RESOURCE_QUOTA, get_network_configs
from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvKey, DevSandboxStatus, SourceCodeFetchMethod
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Runtime, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.labels import get_dev_sandbox_labels
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox

DEV_SANDBOX_CODE_ANNOTATION_KEY = "bkapp.paas.bk.tencent.com/dev-sandbox-code"


class DevSandboxSerializer(AppEntitySerializer["DevSandbox"]):
    def serialize(self, obj: "DevSandbox", original_obj: Optional[ResourceInstance] = None, **kwargs):
        return {
            "apiVersion": self.get_apiversion(),
            "kind": "Pod",
            "metadata": {
                "name": obj.name,
                "labels": get_dev_sandbox_labels(obj.app),
                "annotations": {DEV_SANDBOX_CODE_ANNOTATION_KEY: obj.code},
            },
            "spec": self._construct_pod_spec(obj),
        }

    def _construct_pod_spec(self, obj: "DevSandbox") -> Dict:
        spec = {"containers": [self._construct_main_container(obj)]}
        self._set_volume_mounts(spec, obj)
        return spec

    def _construct_main_container(self, obj: "DevSandbox") -> Dict:
        return {
            "name": "main",
            "image": obj.runtime.image,
            "imagePullPolicy": obj.runtime.image_pull_policy,
            "env": self._construct_container_envs(obj),
            "ports": [
                {
                    "containerPort": cfg.target_port,
                }
                for cfg in get_network_configs(obj)
            ],
            "readinessProbe": {
                "exec": {"command": ["check-health"]},
            },
            "resources": DEV_SANDBOX_RESOURCE_QUOTA.to_dict(),
        }

    @staticmethod
    def _construct_container_envs(obj: "DevSandbox") -> List[Dict]:
        """容器环境变量配置"""
        envs = [
            {
                "name": str(key),
                "value": str(value),
            }
            for key, value in obj.runtime.envs.items()
        ]
        if obj.code_editor_cfg:
            envs.extend(
                [
                    {
                        "name": DevSandboxEnvKey.CODE_EDITOR_PASSWORD.value,
                        "value": obj.code_editor_cfg.password,
                    },
                    {
                        "name": DevSandboxEnvKey.ENABLE_CODE_EDITOR.value,
                        "value": "true",
                    },
                ]
            )

        return envs

    @staticmethod
    def _set_volume_mounts(spec: Dict, obj: "DevSandbox"):
        """容器挂载卷配置"""

        # 目前只有启用代码编辑器时，需要配置挂载卷
        if not obj.code_editor_cfg:
            return

        spec["volumes"] = [
            {
                "name": "code-editor-config",
                "configMap": {"name": f"{obj.name}-code-editor-config"},
            }
        ]
        # 目前只会有一个容器
        spec["containers"][0]["volumeMounts"] = [
            {
                "name": "code-editor-config",
                # 参考文档：
                # https://github.com/coder/code-server/blob/main/docs/FAQ.md#how-does-the-config-file-work
                # https://github.com/coder/code-server/blob/main/docs/FAQ.md#where-is-vs-code-configuration-stored
                "mountPath": "/tmp/code-editor-config/settings.json",
                "subPath": "settings.json",
            }
        ]


class DevSandboxDeserializer(AppEntityDeserializer["DevSandbox"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "DevSandbox":
        main_container = kube_data.spec.containers[0]
        envs = {env.name: getattr(env, "value", "") for env in main_container.env}

        code = ""
        if annos := kube_data.metadata.annotations:
            code = annos.get(DEV_SANDBOX_CODE_ANNOTATION_KEY, "")

        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            code=code,
            runtime=Runtime(
                envs=envs,
                image=main_container.image,
                image_pull_policy=main_container.imagePullPolicy,
            ),
            source_code_cfg=self._get_source_code_cfg_from_envs(envs),
            code_editor_cfg=self._get_code_editor_cfg_from_envs(envs),
            status=self._get_dev_sandbox_status(kube_data),
        )

    @staticmethod
    def _get_source_code_cfg_from_envs(envs: Dict[str, str]) -> SourceCodeConfig:
        return SourceCodeConfig(
            source_fetch_url=envs.get(DevSandboxEnvKey.SOURCE_FETCH_URL),
            source_fetch_method=SourceCodeFetchMethod(
                envs.get(DevSandboxEnvKey.SOURCE_FETCH_METHOD, SourceCodeFetchMethod.HTTP.value),
            ),
        )

    @staticmethod
    def _get_code_editor_cfg_from_envs(envs: Dict[str, str]) -> CodeEditorConfig | None:
        if code_editor_password := envs.get(DevSandboxEnvKey.CODE_EDITOR_PASSWORD):
            return CodeEditorConfig(password=code_editor_password)

        return None

    @staticmethod
    def _get_dev_sandbox_status(pod: ResourceInstance) -> DevSandboxStatus:
        """沙箱 Ready 条件：所有容器都已经 Ready"""
        if not getattr(pod, "status"):
            return DevSandboxStatus.PENDING

        container_statuses = getattr(pod.status, "containerStatuses")
        if not container_statuses:
            return DevSandboxStatus.PENDING

        if len(container_statuses) != len(pod.spec.containers):
            return DevSandboxStatus.PENDING

        for cs in container_statuses:
            if not cs.ready:
                return DevSandboxStatus.PENDING

        return DevSandboxStatus.READY
