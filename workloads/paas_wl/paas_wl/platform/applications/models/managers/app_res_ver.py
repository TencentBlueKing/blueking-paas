# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings

from paas_wl.resources.base.generation import check_if_available, get_mapper_version
from paas_wl.resources.utils.basic import get_client_by_app

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.app import App
    from paas_wl.resources.base.generation import MapperPack

logger = logging.getLogger(__name__)


@dataclass
class AppResVerManager:
    """应用资源版本管理器"""

    _mapper_version_term: str = "mapper_version"

    def __init__(self, app: 'App'):
        self.app = app
        self.client = get_client_by_app(app)

    @property
    def curr_version(self) -> 'MapperPack':
        """获取当前版本"""
        latest_config = self.app.latest_config

        # 一般对于只读的操作，都只需要直接读取当前版本
        return get_mapper_version(
            target=latest_config.metadata.get(self._mapper_version_term, settings.LEGACY_MAPPER_VERSION),
            init_kwargs=dict(client=self.client),
        )

    def update(self, version: str):
        """更新应用的 mapper 版本"""
        check_if_available(version)
        latest_config = self.app.latest_config

        metadata = latest_config.metadata or {}
        metadata.update({self._mapper_version_term: version})
        setattr(latest_config, 'metadata', metadata)

        latest_config.save(update_fields=['metadata', 'updated'])
