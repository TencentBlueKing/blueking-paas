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

from dataclasses import dataclass

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.conf import DEV_SANDBOX_WORKSPACE
from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvKey, PodPhase
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Runtime, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.kres_slzs import DevSandboxDeserializer, DevSandboxSerializer
from paas_wl.bk_app.dev_sandbox.names import get_dev_sandbox_name
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity


@dataclass
class DevSandbox(AppEntity):
    """开发沙箱"""

    # 唯一标识
    code: str
    # 镜像，环境变量等信息
    runtime: Runtime
    # 源码相关配置
    source_code_cfg: SourceCodeConfig
    # 代码编辑器配置
    code_editor_cfg: CodeEditorConfig | None = None
    # 部署后, 从集群中获取状态
    phase: str = PodPhase.UNKNOWN

    class Meta:
        kres_class = kres.KPod
        serializer = DevSandboxSerializer
        deserializer = DevSandboxDeserializer

    @classmethod
    def create(
        cls,
        wl_app: WlApp,
        code: str,
        token: str,
        runtime: Runtime,
        source_code_cfg: SourceCodeConfig,
        code_editor_cfg: CodeEditorConfig | None = None,
    ) -> "DevSandbox":
        # 注入特殊环境变量

        # 沙箱服务
        runtime.envs[DevSandboxEnvKey.WORKSPACE] = DEV_SANDBOX_WORKSPACE
        runtime.envs[DevSandboxEnvKey.TOKEN] = token
        # 源代码信息
        runtime.envs[DevSandboxEnvKey.SOURCE_FETCH_METHOD] = str(source_code_cfg.source_fetch_method)
        runtime.envs[DevSandboxEnvKey.SOURCE_FETCH_URL] = source_code_cfg.source_fetch_url or ""
        # 代码编辑器配置
        if code_editor_cfg:
            runtime.envs[DevSandboxEnvKey.CODE_EDITOR_PASSWORD] = code_editor_cfg.password
            runtime.envs[DevSandboxEnvKey.CODE_EDITOR_START_DIR] = DEV_SANDBOX_WORKSPACE
            # 禁用遥测，不支持收集数据
            runtime.envs[DevSandboxEnvKey.CODE_EDITOR_DISABLE_TELEMETRY] = "true"

        return cls(
            app=wl_app,
            name=get_dev_sandbox_name(wl_app),
            code=code,
            runtime=runtime,
            source_code_cfg=source_code_cfg,
            code_editor_cfg=code_editor_cfg,
        )
