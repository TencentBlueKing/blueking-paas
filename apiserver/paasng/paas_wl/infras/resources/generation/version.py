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
from collections import OrderedDict
from typing import TYPE_CHECKING, Dict, Optional, Type

from django.conf import settings

from paas_wl.bk_app.applications.models.release import Release
from paas_wl.infras.resources.generation.mapper import MapperProcConfig
from paas_wl.infras.resources.generation.v1 import V1Mapper
from paas_wl.infras.resources.generation.v2 import V2Mapper
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.utils.command import get_command_name

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp
    from paas_wl.infras.resources.generation.mapper import MapperPack

logger = logging.getLogger(__name__)

# 按照 version 添加的顺序
AVAILABLE_GENERATIONS: Dict[str, Type['MapperPack']] = OrderedDict(v1=V1Mapper, v2=V2Mapper)


class AppResVerManager:
    """应用资源版本管理器"""

    def __init__(self, app: 'WlApp'):
        self.app = app
        self._mapper_version_term: str = "mapper_version"

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
        """更新应用的 mapper 版本

        :raise ValueError: When the version is not available.
        """
        if version not in AVAILABLE_GENERATIONS:
            raise ValueError("%s is not available, please choose version in %s", version, AVAILABLE_GENERATIONS.keys())

        latest_config = self.app.latest_config

        metadata = latest_config.metadata or {}
        metadata.update({self._mapper_version_term: version})
        setattr(latest_config, 'metadata', metadata)

        latest_config.save(update_fields=['metadata', 'updated'])


def get_mapper_version(target: str, init_kwargs: Optional[dict] = None):
    available_packs = dict()
    for generation, mapper_class in AVAILABLE_GENERATIONS.items():
        available_packs[generation] = mapper_class(**init_kwargs or {})
    return available_packs[target]


def get_latest_mapper_version(init_kwargs: Optional[dict] = None):
    """获取最新的 mapper version"""
    target = list(AVAILABLE_GENERATIONS.keys())[-1]
    return AVAILABLE_GENERATIONS[target](**init_kwargs or {})


def get_proc_deployment_name(app: 'WlApp', process_type: str) -> str:
    """A shortcut function which gets the name of deployment resource for the given
    app and process_type.
    """
    mapper_version = AppResVerManager(app).curr_version

    # Get the command name by reading the latest successful release, when failed, use
    # an empty command name instead. The empty command name may generate wrong result
    # when the algorithm of the mapper's algorithm relies on it.
    #
    # TODO: Remove this logic entirely when the mapper version was removed.
    try:
        release = Release.objects.get_latest(app)
        version = release.version
        command_name = get_command_name(release.get_procfile()[process_type])
    except (Release.DoesNotExist, KeyError):
        logger.warning('Unable to get the deployment name of %s, app: %s', process_type, app)
        version = 1
        command_name = ''

    proc_config = MapperProcConfig(app=app, type=process_type, version=version, command_name=command_name)
    return mapper_version.deployment(process=proc_config).name
