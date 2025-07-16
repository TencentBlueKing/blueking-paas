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

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

from paas_wl.bk_app.dev_sandbox.kres_slzs.configmap import (
    DevSandboxConfigMapDeserializer,
    DevSandboxConfigMapSerializer,
)
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox


@dataclass
class DevSandboxConfigMap(AppEntity):
    data: Dict[str, str]

    class Meta:
        kres_class = kres.KConfigMap
        serializer = DevSandboxConfigMapSerializer
        deserializer = DevSandboxConfigMapDeserializer

    @classmethod
    def create(cls, dev_sandbox: "DevSandbox") -> "DevSandboxConfigMap":
        cfg_mp_name = f"{dev_sandbox.name}-code-editor-config"

        data = {
            "settings.json": json.dumps(
                # workbench.colorTheme 用于设置编辑器的默认配色；window.autoDetectColorScheme 用于配置编辑器颜色不随系统主题颜色变化
                # 参考文档：
                # https://code.visualstudio.com/docs/configure/themes#_color-themes
                # https://code.visualstudio.com/docs/configure/themes#_automatically-switch-based-on-os-color-scheme
                {"workbench.colorTheme": "Visual Studio Dark", "window.autoDetectColorScheme": False}
            )
        }

        return cls(app=dev_sandbox.app, name=cfg_mp_name, data=data)
