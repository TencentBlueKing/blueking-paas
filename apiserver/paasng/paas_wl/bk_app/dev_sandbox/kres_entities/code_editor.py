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
from typing import Optional

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Resources, Runtime, Status
from paas_wl.bk_app.dev_sandbox.kres_slzs import CodeEditorDeserializer, CodeEditorSerializer
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity


@dataclass
class CodeEditor(AppEntity):
    """CodeEditor entity"""

    runtime: Runtime
    resources: Optional[Resources] = None
    # 部署后, 从集群中获取状态
    status: Optional[Status] = None
    # 编辑器相关配置
    config: Optional[CodeEditorConfig] = None

    class Meta:
        kres_class = kres.KDeployment
        serializer = CodeEditorSerializer
        deserializer = CodeEditorDeserializer

    @classmethod
    def create(
        cls,
        dev_wl_app: WlApp,
        runtime: Runtime,
        config: CodeEditorConfig,
        resources: Optional[Resources] = None,
    ) -> "CodeEditor":
        return cls(
            app=dev_wl_app,
            name=get_code_editor_name(dev_wl_app),
            config=config,
            runtime=runtime,
            resources=resources,
        )

    def construct_envs(self):
        """该函数将 CodeEditor 对象的属性(需要通过环境变量生效的配置)注入环境变量"""
        if not self.config:
            return

        envs = self.runtime.envs

        def update_env_var(key, value):
            if value:
                envs.update({key: value})

        # 注入登陆密码环境变量
        update_env_var("PASSWORD", self.config.password)
        # 注入启动目录环境变量
        update_env_var("START_DIR", self.config.start_dir)


def get_code_editor_name(dev_wl_app: WlApp) -> str:
    return f"{dev_wl_app.scheduler_safe_name}-code-editor"
