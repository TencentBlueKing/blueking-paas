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

from typing import TYPE_CHECKING, List

from django.conf import settings

from paas_wl.bk_app.dev_sandbox.entities import NetworkConfig, Resources, ResourceSpec

if TYPE_CHECKING:
    from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox


DEV_SERVER_NETWORK_CONFIG = NetworkConfig(
    path_prefix="/devserver/",
    port_name="devserver",
    port=8000,
    target_port=settings.DEV_SANDBOX_DEVSERVER_PORT,
)

APP_SERVER_NETWORK_CONFIG = NetworkConfig(
    path_prefix="/app/",
    port_name="app",
    port=80,
    target_port=settings.CONTAINER_PORT,
)

CODE_EDITOR_NETWORK_CONFIG = NetworkConfig(
    path_prefix="/code_editor/",
    port_name="code-editor",
    port=10251,
    target_port=settings.DEV_SANDBOX_CODE_EDITOR_PORT,
)


def get_network_configs(dev_sandbox: "DevSandbox") -> List[NetworkConfig]:
    cfgs = [DEV_SERVER_NETWORK_CONFIG, APP_SERVER_NETWORK_CONFIG]

    # 只有配置启用代码编辑器，才会提供相应的网络配置
    if dev_sandbox.code_editor_cfg:
        cfgs.append(CODE_EDITOR_NETWORK_CONFIG)

    return cfgs


# 开发沙箱默认资源配额
DEV_SANDBOX_RESOURCE_QUOTA = Resources(
    limits=ResourceSpec(cpu="4", memory="2Gi"),
    requests=ResourceSpec(cpu="500m", memory="1Gi"),
)

# 默认工作空间
DEV_SANDBOX_WORKSPACE = "/data/workspace"
