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
from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

from paasng.platform.mgrlegacy.entities import DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import BackupLegacyDataFailed, MigrationFailed, RollbackFailed
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess

logger = logging.getLogger(__name__)


class CNativeBaseMigrator(ABC):
    """cloud-native base migrator

    :param migration_process: CNativeMigrationProcess
    """

    _classes_map: Dict[str, Type["CNativeBaseMigrator"]] = {}

    def __init__(self, migration_process: CNativeMigrationProcess):
        self.migration_process = migration_process
        self.app = migration_process.app

    def __init_subclass__(cls, **kwargs):
        cls._classes_map[cls.__name__] = cls

    @classmethod
    def get_class(cls, cls_name: str):
        return cls._classes_map[cls_name]

    @classmethod
    def get_name(cls):
        return cls.__name__

    def migrate(self):
        """migrate from default app(普通应用) to cloud native app"""
        self._can_migrate_or_raise()

        try:
            if legacy_data := self._generate_legacy_data():
                self._backup_legacy_data(legacy_data)
        except Exception as e:
            raise BackupLegacyDataFailed(f"backup data failed: {e}")

        try:
            self._migrate()
        except Exception as e:
            raise MigrationFailed(f"migrate failed: {e}")

    def rollback(self):
        """rollback from cloud native app to default app(普通应用)"""
        try:
            self._rollback()
        except Exception as e:
            logger.exception(f"migration_process(id={self.migration_process.id}) rollback failed")
            raise RollbackFailed(f"rollback failed: {e}")

    def _backup_legacy_data(self, legacy_data: DefaultAppLegacyData):
        """backup legacy data for rollback"""
        self.migration_process.legacy_data = legacy_data
        self.migration_process.save(update_fields=["legacy_data"])

    @abstractmethod
    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        """generate legacy data"""
        raise NotImplementedError()

    @abstractmethod
    def _migrate(self):
        """actual migration logic"""
        raise NotImplementedError()

    @abstractmethod
    def _can_migrate_or_raise(self):
        """
        check if the migrator can run migrate

        :raise PreCheckMigrationFailed: if the migration pre-condition is not met
        """
        raise NotImplementedError()

    @abstractmethod
    def _rollback(self):
        """actual rollback logic"""
        raise NotImplementedError()
