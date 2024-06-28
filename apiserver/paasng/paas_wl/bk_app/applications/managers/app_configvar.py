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

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

from django.conf import settings

from paas_wl.bk_app.applications.managers.app_metadata import get_metadata

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp

logger = logging.getLogger(__name__)


def get_default_subpath(app: "WlApp") -> str:
    """Get the default sub path for given application, this value will be used for:

    - sub path based ingress resource, used as request accessing location
    - injected builtin env variable: BKPAAS_SUB_PATH
    """
    return f"/{app.region}-{app.name}/"


@dataclass
class AppConfigVarManager:
    """应用相关的环境变量生成器

    职责: 管理与 `应用`和 `应用进程` 相关的环境变量, 例如日志路径, 应用ID, 模块名称 等等, 不涉及与具体运行版本相关的配置
    """

    app: "WlApp"

    def __post_init__(self):
        self.metadata = get_metadata(self.app)

    @staticmethod
    def add_prefix(key: str) -> str:
        return settings.SYSTEM_CONFIG_VARS_KEY_PREFIX + key

    def get_process_envs(self, process_type: str) -> Dict:
        config_vars = self.get_envs()
        config_vars.update(
            {
                self.add_prefix("LOG_NAME_PREFIX"): (
                    f"{self.app.region}-bkapp-"
                    f"{self.metadata.get_paas_app_code()}-"
                    f"{self.metadata.environment}-{process_type}"
                ),
                self.add_prefix("PROCESS_TYPE"): process_type,
            }
        )
        return config_vars

    def get_envs(self) -> Dict:
        config_vars = {
            self.add_prefix("APP_LOG_PATH"): settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
            # May be overwrite by paasng module
            self.add_prefix("SUB_PATH"): get_default_subpath(self.app),
        }
        # TODO: 使用更好的方式把端口暴露给用户
        config_vars.update({"PORT": str(settings.CONTAINER_PORT)})
        return config_vars
