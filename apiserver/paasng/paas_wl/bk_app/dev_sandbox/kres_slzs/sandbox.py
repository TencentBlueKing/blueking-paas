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

from django.conf import settings
from kubernetes.dynamic import ResourceField, ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.conf import (
    APP_SERVER_NETWORK_CONFIG,
    CODE_EDITOR_NETWORK_CONFIG,
    CODE_EDITOR_RESOURCE_QUOTA,
    DEV_SANDBOX_WORKSPACE,
    DEV_SERVER_NETWORK_CONFIG,
    DEV_SERVER_RESOURCE_QUOTA,
)
from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvKey, DevSandboxStatus, SourceCodeFetchMethod
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Runtime, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.labels import get_dev_sandbox_labels
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox

DEV_SERVER_CONTAINER_NAME = "dev-sandbox"

CODE_EDITOR_CONTAINER_NAME = "code-editor"

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
        containers = [self._construct_dev_sandbox_container(obj)]

        if obj.code_editor_cfg:
            containers.append(self._construct_code_editor_container(obj))

        spec = {"containers": containers}
        self._set_volume_mounts(spec, obj)

        return spec

    @staticmethod
    def _construct_dev_sandbox_container(obj: "DevSandbox") -> Dict:
        return {
            "name": DEV_SERVER_CONTAINER_NAME,
            "image": obj.runtime.image,
            "env": [
                {
                    "name": str(key),
                    "value": str(value),
                }
                for key, value in obj.runtime.envs.items()
            ],
            "imagePullPolicy": obj.runtime.image_pull_policy,
            "ports": [
                {
                    "containerPort": config.target_port,
                }
                for config in [DEV_SERVER_NETWORK_CONFIG, APP_SERVER_NETWORK_CONFIG]
            ],
            "readinessProbe": {
                "httpGet": {
                    "port": settings.DEV_SANDBOX_DEVSERVER_PORT,
                    "path": "/healthz",
                },
            },
            "resources": DEV_SERVER_RESOURCE_QUOTA.to_dict(),
        }

    @staticmethod
    def _construct_code_editor_container(obj: "DevSandbox") -> Dict:
        return {
            "name": CODE_EDITOR_CONTAINER_NAME,
            "image": settings.DEV_SANDBOX_CODE_EDITOR_IMAGE,
            "command": ["/usr/bin/code-server"],
            # --disable-telemetry 禁止遥测数据收集功能；--disable-update-check 关闭 code-server 自动更新
            # 参考文档：
            # https://code.visualstudio.com/docs/configure/telemetry
            # https://code.visualstudio.com/docs/supporting/FAQ#_telemetry-and-crash-reporting
            # https://code.visualstudio.com/docs/supporting/FAQ#_how-do-i-opt-out-of-vs-code-autoupdates
            "args": ["--bind-addr", "0.0.0.0:8080", "--disable-telemetry", "--disable-update-check"],
            # 代码编辑器仅需要少量的环境变量
            "env": [
                {
                    "name": DevSandboxEnvKey.CODE_EDITOR_PASSWORD.value,
                    "value": obj.code_editor_cfg.password if obj.code_editor_cfg else "",
                },
                # 禁用遥测，不支持收集数据
                {
                    "name": DevSandboxEnvKey.CODE_EDITOR_DISABLE_TELEMETRY.value,
                    "value": "true",
                },
            ],
            "imagePullPolicy": "IfNotPresent",
            "ports": [
                {
                    "containerPort": CODE_EDITOR_NETWORK_CONFIG.target_port,
                },
            ],
            "readinessProbe": {
                "httpGet": {
                    "port": settings.DEV_SANDBOX_CODE_EDITOR_PORT,
                    "path": "/healthz",
                },
            },
            "resources": CODE_EDITOR_RESOURCE_QUOTA.to_dict(),
        }

    @staticmethod
    def _set_volume_mounts(spec: Dict, obj: "DevSandbox"):
        """为开发沙箱设置挂载卷"""
        spec["volumes"] = [
            {
                "name": "workspace",
                "emptyDir": {"sizeLimit": "1Gi"},
            }
        ]

        if obj.code_editor_cfg:
            spec["volumes"].append(
                {
                    "name": "code-editor-config",
                    "configMap": {
                        "name": f"{obj.name}-code-editor-config",
                    },
                }
            )

        for container in spec["containers"]:
            container["volumeMounts"] = [
                {
                    "name": "workspace",
                    "mountPath": DEV_SANDBOX_WORKSPACE,
                }
            ]

            if container["name"] == CODE_EDITOR_CONTAINER_NAME and obj.code_editor_cfg:
                container["volumeMounts"].append(
                    {
                        "name": "code-editor-config",
                        # 参考文档：
                        # https://github.com/coder/code-server/blob/main/docs/FAQ.md#how-does-the-config-file-work
                        # https://github.com/coder/code-server/blob/main/docs/FAQ.md#where-is-vs-code-configuration-stored
                        "mountPath": "/home/coder/.local/share/code-server/User/settings.json",
                        "subPath": "settings.json",
                    }
                )


class DevSandboxDeserializer(AppEntityDeserializer["DevSandbox"]):
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "DevSandbox":
        dev_server_container = self._get_dev_server_container(kube_data)
        envs = {env.name: getattr(env, "value", "") for env in dev_server_container.env}

        code = ""
        if annos := kube_data.metadata.annotations:
            code = annos.get(DEV_SANDBOX_CODE_ANNOTATION_KEY, "")

        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            code=code,
            runtime=Runtime(
                envs=envs,
                image=dev_server_container.image,
                image_pull_policy=dev_server_container.imagePullPolicy,
            ),
            source_code_cfg=self._get_source_code_cfg_from_envs(envs),
            code_editor_cfg=self._get_code_editor_cfg_from_envs(envs),
            status=self._get_dev_sandbox_status(kube_data),
        )

    @staticmethod
    def _get_dev_server_container(pod: ResourceInstance) -> ResourceField:
        for c in pod.spec.containers:
            if c.name == DEV_SERVER_CONTAINER_NAME:
                return c

        raise AttributeError(f"No {DEV_SERVER_CONTAINER_NAME} container found in resource")

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
