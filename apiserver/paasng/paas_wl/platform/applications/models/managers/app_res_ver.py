# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings

from paas_wl.deploy.app_res.generation import check_if_available, get_mapper_version
from paas_wl.resources.utils.basic import get_client_by_app

if TYPE_CHECKING:
    from paas_wl.deploy.app_res.generation import MapperPack
    from paas_wl.platform.applications.models import WlApp

logger = logging.getLogger(__name__)


@dataclass
class AppResVerManager:
    """应用资源版本管理器"""

    _mapper_version_term: str = "mapper_version"

    def __init__(self, app: 'WlApp'):
        self.app = app

    @property
    def curr_version(self) -> 'MapperPack':
        """获取当前版本"""
        latest_config = self.app.latest_config

        # 一般对于只读的操作，都只需要直接读取当前版本
        client = get_client_by_app(self.app)
        return get_mapper_version(
            target=latest_config.metadata.get(self._mapper_version_term) or settings.LEGACY_MAPPER_VERSION,
            init_kwargs=dict(client=client),
        )

    def update(self, version: str):
        """更新应用的 mapper 版本"""
        check_if_available(version)
        latest_config = self.app.latest_config

        metadata = latest_config.metadata or {}
        metadata.update({self._mapper_version_term: version})
        setattr(latest_config, 'metadata', metadata)

        latest_config.save(update_fields=['metadata', 'updated'])
